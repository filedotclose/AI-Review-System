'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import apiClient, { isOfflineQueued } from '@/lib/api-client';
import { compressImage, fileToDataUrl } from '@/lib/image-compression';
import { useAuth } from '@/lib/auth-context';
import {
  PlusCircle,
  Receipt,
  Camera,
  ShieldCheck,
  Check,
  CheckCircle2,
  Ban,
  ArrowUpRight,
  Layers,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { Modal } from '@/components/ui/Modal';
import { Toast } from '@/components/ui/Toast';
import { MaskedField } from '@/components/ui/MaskedField';

interface ExpenseItem {
  id: number | string;
  amount: number;
  category: string;
  description: string;
  date: string;
  is_out_of_pocket: boolean;
  approval_status: string;
  reimbursement_status: string;
  duplicate_flag?: boolean;
  has_physical_bill?: boolean;
  receipt_photo_url?: string;
  created_at?: string;
}

const INITIAL_EXPENSES: ExpenseItem[] = [];

const generateOfflineTxId = (): string => 'offline-' + Date.now();

export default function PettyCashPage() {
  const { user } = useAuth();
  const [siteId] = useState('1');
  const [walletBalance, setWalletBalance] = useState(14500.0);
  const [supervisorDeficit, setSupervisorDeficit] = useState(2050.0);
  const [expenses, setExpenses] = useState<ExpenseItem[]>(INITIAL_EXPENSES);

  // Role Differentiation Flags
  const isFinanceOrOwner = user?.role === 'FINANCE_HEAD' || user?.role === 'OWNER';
  const isSupervisorOrEngineer = user?.role === 'SUPERVISOR' || user?.role === 'SITE_ENGINEER';

  // Active Tab
  const [activeTab, setActiveTab] = useState<'approvals' | 'ledger' | 'entry'>(
    user?.role === 'FINANCE_HEAD' ? 'approvals' : 'ledger'
  );

  useEffect(() => {
    if (user?.role === 'FINANCE_HEAD') {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveTab('approvals');
    } else if (user?.role === 'SUPERVISOR') {
      setActiveTab('entry');
    }
  }, [user?.role]);

  // Modals
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  const [isReimburseModalOpen, setIsReimburseModalOpen] = useState(false);
  const [isReplenishModalOpen, setIsReplenishModalOpen] = useState(false);
  const [isSettleModalOpen, setIsSettleModalOpen] = useState(false);
  const [settleTargetTx, setSettleTargetTx] = useState<ExpenseItem | null>(null);
  const [settleUtrRef, setSettleUtrRef] = useState('');
  const [receiptModalUrl, setReceiptModalUrl] = useState<string | null>(null);

  // Form State
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('DIESEL');
  const [description, setDescription] = useState('');
  const [expenseDate, setExpenseDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('Liters');
  const [isOutOfPocket, setIsOutOfPocket] = useState(false);
  const [hasPhysicalBill, setHasPhysicalBill] = useState(true);

  // Receipt image
  const [receiptPhoto, setReceiptPhoto] = useState<{ name: string; size: number; compressedSize: number; dataUrl: string } | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);

  // Reimbursement State
  const [reimburseRef, setReimburseRef] = useState('');
  const [reimburseAmount, setReimburseAmount] = useState('2050');

  // Replenish State
  const [replenishAmount, setReplenishAmount] = useState('25000');
  const [replenishDesc, setReplenishDesc] = useState('Weekly site petty cash replenishment');

  // UI Feedback
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'warning' | 'error' | 'info'; text: string } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [filterCategory, setFilterCategory] = useState<string>('ALL');

  // Fetch live wallet balance from backend if available
  const fetchWallet = useCallback(async () => {
    try {
      const res = await apiClient.get(`/petty-cash/wallet/${siteId}`);
      if (res.data) {
        setWalletBalance(res.data.current_balance ?? 0);
        setSupervisorDeficit(res.data.supervisor_deficit ?? 0);
      }
    } catch {
      // Backend may not be reachable in pure offline mode
    }
  }, [siteId]);

  // Fetch live expenses from backend
  const fetchExpenses = useCallback(async () => {
    try {
      const res = await apiClient.get(`/petty-cash/expenses?site_id=${siteId}`);
      if (Array.isArray(res.data)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const liveItems: ExpenseItem[] = res.data.map((tx: any) => ({
          id: tx.id,
          amount: tx.amount,
          category: tx.category,
          description: tx.description,
          date: typeof tx.date === 'string' ? tx.date : new Date(tx.date).toISOString().split('T')[0],
          is_out_of_pocket: tx.is_out_of_pocket,
          approval_status: tx.approval_status,
          reimbursement_status: tx.reimbursement_status,
          has_physical_bill: tx.has_physical_bill,
          receipt_photo_url: tx.receipt_photo_url,
          created_at: tx.created_at,
        }));
        setExpenses(liveItems);
      }
    } catch {
      // Backend may not be reachable in pure offline mode
    }
  }, [siteId]);

  useEffect(() => {
    fetchWallet();
    fetchExpenses();
  }, [fetchWallet, fetchExpenses]);

  // Duplicate check logic
  const duplicateWarning = useMemo(() => {
    const numAmount = parseFloat(amount);
    if (!numAmount || isNaN(numAmount)) return null;

    const matched = expenses.find((exp) => {
      const diffAmount = Math.abs(exp.amount - numAmount);
      return diffAmount < 0.01 && exp.category === category;
    });

    if (matched) {
      return `Potential duplicate detected! An expense of ₹${matched.amount.toLocaleString('en-IN')} in category ${matched.category} was already recorded on ${matched.date}.`;
    }
    return null;
  }, [amount, category, expenses]);

  // Deficit Cap check
  const deficitCapWarning = useMemo(() => {
    const numAmount = parseFloat(amount) || 0;
    const projectedDeficit = isOutOfPocket
      ? supervisorDeficit + numAmount
      : walletBalance - numAmount < 0
      ? supervisorDeficit + Math.abs(walletBalance - numAmount)
      : supervisorDeficit;

    if (projectedDeficit > 50000) {
      return {
        isExceeded: true,
        message: `Strict Deficit Cap Exceeded: Projected out-of-pocket deficit ₹${projectedDeficit.toLocaleString('en-IN')} exceeds the maximum ₹50,000 threshold.`,
      };
    } else if (projectedDeficit > 40000) {
      return {
        isExceeded: false,
        message: `High Deficit Advisory: Projected deficit is ₹${projectedDeficit.toLocaleString('en-IN')} (₹${(50000 - projectedDeficit).toLocaleString('en-IN')} remaining before ₹50,000 cap).`,
      };
    }
    return null;
  }, [amount, isOutOfPocket, supervisorDeficit, walletBalance]);

  // Handle Receipt Photo Upload with Compression
  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsCompressing(true);
    try {
      const compressed = await compressImage(file, 1200, 0.7);
      const dataUrl = await fileToDataUrl(compressed);
      setReceiptPhoto({
        name: file.name,
        size: file.size,
        compressedSize: compressed.size,
        dataUrl,
      });
    } catch (err) {
      console.error('Receipt compression error:', err);
    } finally {
      setIsCompressing(false);
      e.target.value = '';
    }
  };

  // Log Expense Submission
  const handleExpenseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (deficitCapWarning?.isExceeded) {
      setToastMessage({
        type: 'error',
        text: 'Cannot submit: Deficit exceeds ₹50,000 limit.',
      });
      return;
    }

    const numAmount = parseFloat(amount);
    if (!numAmount || numAmount <= 0) {
      setToastMessage({ type: 'error', text: 'Expense amount must be strictly positive.' });
      return;
    }

    setIsSubmitting(true);
    setToastMessage(null);

    const payload = {
      site_id: parseInt(siteId, 10),
      amount: numAmount,
      category,
      description,
      date: expenseDate,
      quantity: quantity ? parseFloat(quantity) : null,
      unit: quantity ? unit : null,
      is_out_of_pocket: isOutOfPocket,
      has_physical_bill: hasPhysicalBill,
      receipt_photo: receiptPhoto?.dataUrl || null,
    };

    try {
      const res = await apiClient.post('/petty-cash/expenses', payload);
      const createdTx: ExpenseItem = res.data;

      setExpenses((prev) => [createdTx, ...prev]);

      if (isOutOfPocket) {
        setSupervisorDeficit((prev) => prev + numAmount);
      } else {
        setWalletBalance((prev) => prev - numAmount);
      }

      setToastMessage({
        type: 'success',
        text: `Expense of ₹${numAmount.toLocaleString('en-IN')} recorded successfully.`,
      });
      setIsExpenseModalOpen(false);
      resetExpenseForm();
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        const queuedTx: ExpenseItem = {
          id: generateOfflineTxId(),
          amount: numAmount,
          category,
          description: `[Offline] ${description}`,
          date: expenseDate,
          is_out_of_pocket: isOutOfPocket,
          approval_status: 'PENDING',
          reimbursement_status: isOutOfPocket ? 'DUE' : 'NOT_APPLICABLE',
          has_physical_bill: hasPhysicalBill,
        };
        setExpenses((prev) => [queuedTx, ...prev]);

        if (isOutOfPocket) {
          setSupervisorDeficit((prev) => prev + numAmount);
        } else {
          setWalletBalance((prev) => prev - numAmount);
        }

        setToastMessage({
          type: 'warning',
          text: `Expense of ₹${numAmount.toLocaleString('en-IN')} saved offline. Will sync when reconnected.`,
        });
        setIsExpenseModalOpen(false);
        resetExpenseForm();
      } else {
        const error = err as { response?: { data?: { detail?: string } }; message?: string };
        const detail = error.response?.data?.detail || error.message || 'Failed to log expense.';
        setToastMessage({ type: 'error', text: detail });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetExpenseForm = () => {
    setAmount('');
    setDescription('');
    setQuantity('');
    setUnit('Liters');
    setIsOutOfPocket(false);
    setReceiptPhoto(null);
  };

  // Reimbursement Request Submission
  const handleReimburseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const reimbAmt = parseFloat(reimburseAmount);
    if (!reimbAmt || reimbAmt <= 0) return;

    setIsSubmitting(true);
    try {
      await apiClient.post('/petty-cash/reimbursements', {
        wallet_id: parseInt(siteId, 10),
        amount: reimbAmt,
        reimbursement_ref: reimburseRef || `REIMB-${Date.now().toString().slice(-5)}`,
      });
      setToastMessage({
        type: 'success',
        text: `Reimbursement request of ₹${reimbAmt.toLocaleString('en-IN')} submitted for finance sign-off.`,
      });
      setIsReimburseModalOpen(false);
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        setToastMessage({
          type: 'warning',
          text: `Reimbursement request of ₹${reimbAmt.toLocaleString('en-IN')} queued offline for sync.`,
        });
        setIsReimburseModalOpen(false);
      } else {
        const error = err as { response?: { data?: { detail?: string } }; message?: string };
        setToastMessage({
          type: 'error',
          text: error.response?.data?.detail || 'Failed to submit reimbursement.',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Finance Approval Actions
  const handleApproveExpense = async (id: number | string) => {
    try {
      await apiClient.patch(`/petty-cash/expenses/${id}/approve`, {
        approval_status: 'APPROVED',
        remarks: 'Approved by Finance Controller',
      });
      setExpenses((prev) =>
        prev.map((e) => (e.id === id ? { ...e, approval_status: 'APPROVED' } : e))
      );
      setToastMessage({ type: 'success', text: `Expense #${id} approved successfully.` });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setToastMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to approve expense.' });
    }
  };

  const handleRejectExpense = async (id: number | string) => {
    try {
      await apiClient.patch(`/petty-cash/expenses/${id}/approve`, {
        approval_status: 'REJECTED',
        remarks: 'Rejected by Finance Controller',
      });
      setExpenses((prev) =>
        prev.map((e) => (e.id === id ? { ...e, approval_status: 'REJECTED' } : e))
      );
      setToastMessage({ type: 'success', text: `Expense #${id} marked REJECTED.` });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setToastMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to reject expense.' });
    }
  };

  // Finance Settle Action
  const handleSettleReimbursement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settleTargetTx || !settleUtrRef) return;
    try {
      setIsSubmitting(true);
      await apiClient.post(`/petty-cash/reimbursements/${settleTargetTx.id}/settle`, {
        reimbursement_ref: settleUtrRef,
      });
      setExpenses((prev) =>
        prev.map((e) => (e.id === settleTargetTx.id ? { ...e, reimbursement_status: 'SETTLED' } : e))
      );
      setSupervisorDeficit((prev) => Math.max(0, prev - settleTargetTx.amount));
      setToastMessage({
        type: 'success',
        text: `Reimbursement settled with Bank UTR: ${settleUtrRef}.`,
      });
      setIsSettleModalOpen(false);
      setSettleTargetTx(null);
      setSettleUtrRef('');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setToastMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to settle reimbursement.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Finance Wallet Replenish Action
  const handleReplenishSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(replenishAmount);
    if (!amt || amt <= 0) return;
    try {
      setIsSubmitting(true);
      await apiClient.post('/petty-cash/replenish', {
        wallet_id: parseInt(siteId, 10),
        amount: amt,
        description: replenishDesc,
      });
      setWalletBalance((prev) => prev + amt);
      setToastMessage({
        type: 'success',
        text: `Petty cash wallet replenished by ₹${amt.toLocaleString('en-IN')}.`,
      });
      setIsReplenishModalOpen(false);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setToastMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to replenish wallet.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const pendingApprovalsCount = expenses.filter((e) => e.approval_status === 'PENDING').length;
  const filteredExpenses =
    filterCategory === 'ALL'
      ? expenses
      : expenses.filter((e) => e.category === filterCategory);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6 select-none font-sans">
      {/* Toast Feedback */}
      {toastMessage && (
        <Toast
          message={toastMessage.text}
          type={toastMessage.type}
          onDismiss={() => setToastMessage(null)}
        />
      )}

      {/* Header & Wallet Balances (with MaskedField for Confidentiality) */}
      <div className="bg-surface p-6 rounded-lg border border-border shadow-soft space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-text">
                Site Petty Cash & Commercial Approvals
              </h1>
              <Badge variant="accent" size="sm">
                Financial Audit
              </Badge>
            </div>
            <p className="text-xs text-text-muted mt-1 leading-relaxed">
              Confidential Site Ledger with Automated Duplicate Anomaly Screening & Deficit Protection
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {isFinanceOrOwner && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsReplenishModalOpen(true)}
                leftIcon={<PlusCircle className="h-3.5 w-3.5" />}
              >
                Replenish Float
              </Button>
            )}

            {supervisorDeficit > 0 && isSupervisorOrEngineer && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsReimburseModalOpen(true)}
                leftIcon={<ArrowUpRight className="h-3.5 w-3.5" />}
              >
                Claim Out-of-Pocket
              </Button>
            )}

            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsExpenseModalOpen(true)}
              leftIcon={<PlusCircle className="h-3.5 w-3.5" />}
            >
              Record Site Expense
            </Button>
          </div>
        </div>

        {/* Financial Balance Scorecards (Masked by default for Confidentiality) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 pt-2 border-t border-border">
          <div className="p-4 rounded-lg bg-surface-sunk/60 border border-border space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Site Float Balance
              </span>
              <span className="text-[10px] text-text-faint">Confidential</span>
            </div>
            <div className="text-xl sm:text-2xl font-semibold text-text font-mono">
              <MaskedField value={walletBalance} maskType="currency" />
            </div>
            <span className="text-[11px] text-text-muted block">
              ADANI-ODIPKS Site Office Primary Float
            </span>
          </div>

          <div className="p-4 rounded-lg bg-surface-sunk/60 border border-border space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Supervisor Deficit
              </span>
              <Badge variant={supervisorDeficit > 40000 ? 'danger' : 'warning'} size="sm">
                Out-of-Pocket
              </Badge>
            </div>
            <div className="text-xl sm:text-2xl font-semibold text-status-warning font-mono">
              <MaskedField value={supervisorDeficit} maskType="currency" />
            </div>
            <span className="text-[11px] text-text-muted block">
              Max allowable deficit cap: ₹50,000
            </span>
          </div>

          <div className="p-4 rounded-lg bg-surface-sunk/60 border border-border space-y-1 sm:col-span-2 lg:col-span-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Approvals Queue
              </span>
              <span className="text-[10px] text-text-faint font-mono">
                {pendingApprovalsCount} Pending
              </span>
            </div>
            <div className="text-xl sm:text-2xl font-semibold text-accent font-mono tabular-nums">
              {pendingApprovalsCount} <span className="text-sm font-sans font-normal text-text-muted">Vouchers</span>
            </div>
            <span className="text-[11px] text-text-muted block">
              {pendingApprovalsCount > 0 ? 'Requires controller sign-off' : 'All vouchers reconciled'}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border bg-surface px-4 rounded-t-lg">
        {isFinanceOrOwner && (
          <button
            type="button"
            onClick={() => setActiveTab('approvals')}
            className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-semibold transition-colors cursor-pointer ${
              activeTab === 'approvals'
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            <ShieldCheck className="h-4 w-4" />
            <span>Commercial Approvals</span>
            {pendingApprovalsCount > 0 && (
              <Badge variant="warning" size="sm">
                {pendingApprovalsCount}
              </Badge>
            )}
          </button>
        )}

        <button
          type="button"
          onClick={() => setActiveTab('ledger')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === 'ledger'
              ? 'border-accent text-accent'
              : 'border-transparent text-text-muted hover:text-text'
          }`}
        >
          <Layers className="h-4 w-4" />
          <span>Voucher Ledger</span>
        </button>
      </div>

      {/* TAB 1: Finance Approvals Queue */}
      {isFinanceOrOwner && activeTab === 'approvals' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-1">
            <h2 className="text-sm font-semibold text-text uppercase tracking-wider">
              Pending Vouchers Awaiting Audit ({pendingApprovalsCount})
            </h2>
            <span className="text-xs text-text-faint">
              AI checks for duplicate amounts within 7 days and 48-hour description overlap
            </span>
          </div>

          <div className="space-y-3">
            {expenses
              .filter((e) => e.approval_status === 'PENDING')
              .map((exp) => (
                <Card key={exp.id} padding="md" className="space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
                    <div className="flex items-center gap-3">
                      <div className="h-9 w-9 rounded-pill bg-accent-soft text-accent flex items-center justify-center font-mono text-xs font-semibold border border-accent/20">
                        #{exp.id}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-text text-sm">
                            {exp.description}
                          </span>
                          <Badge variant="neutral" size="sm">
                            {exp.category}
                          </Badge>
                          {exp.is_out_of_pocket && (
                            <Badge variant="warning" size="sm">
                              Out-of-Pocket Claim
                            </Badge>
                          )}
                        </div>
                        <span className="text-xs text-text-muted mt-0.5 block">
                          Recorded on {exp.date} • Physical Bill Present: {exp.has_physical_bill ? 'Yes' : 'No'}
                        </span>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="text-base font-bold font-mono text-text">
                        <MaskedField value={exp.amount} maskType="currency" />
                      </div>
                      <Badge variant="warning" size="sm" className="mt-1">
                        Pending Verification
                      </Badge>
                    </div>
                  </div>

                  {/* Actions for Finance Head */}
                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-2 text-xs text-text-muted">
                      {exp.has_physical_bill && (
                        <button
                          type="button"
                          onClick={() => setReceiptModalUrl('/sample-bill.jpg')}
                          className="text-accent hover:underline flex items-center gap-1"
                        >
                          <Receipt className="h-3.5 w-3.5" />
                          <span>Inspect Bill Voucher</span>
                        </button>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleRejectExpense(exp.id)}
                        leftIcon={<Ban className="h-3.5 w-3.5" />}
                      >
                        Reject
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleApproveExpense(exp.id)}
                        leftIcon={<Check className="h-3.5 w-3.5" />}
                      >
                        Approve Voucher
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}

            {pendingApprovalsCount === 0 && (
              <Card padding="lg" className="text-center py-12 space-y-2">
                <CheckCircle2 className="h-8 w-8 text-status-success mx-auto" />
                <h3 className="text-sm font-semibold text-text">All Petty Cash Vouchers Verified</h3>
                <p className="text-xs text-text-muted max-w-sm mx-auto">
                  No pending expenditures in the queue. All transactions have been audited and signed off.
                </p>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Ledger */}
      {activeTab === 'ledger' && (
        <Card padding="md">
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 w-full">
              <div>
                <CardTitle>Petty Cash Transaction Ledger</CardTitle>
                <CardDescription>All disbursements, reimbursements, and float movements.</CardDescription>
              </div>

              {/* Filter */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted">Category:</span>
                <select
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                  className="bg-surface-sunk border border-border rounded-md text-xs py-1 px-2.5 text-text focus:outline-none"
                >
                  <option value="ALL">All Categories</option>
                  <option value="DIESEL">Diesel</option>
                  <option value="SPARES">Rig Spares</option>
                  <option value="FOOD_WATER">Food & Water</option>
                  <option value="TRANSPORT">Transport</option>
                  <option value="TOOLS">Tools & Consumables</option>
                </select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Voucher</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead align="right">Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Settlement</TableHead>
                  <TableHead align="right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredExpenses.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center" className="py-8 text-xs text-text-muted">
                      No petty cash vouchers recorded yet for this site.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredExpenses.map((exp) => (
                  <TableRow key={exp.id}>
                    <TableCell isNumeric>#{exp.id}</TableCell>
                    <TableCell className="font-mono text-xs">{exp.date}</TableCell>
                    <TableCell>
                      <Badge variant="neutral" size="sm">
                        {exp.category}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs truncate">{exp.description}</TableCell>
                    <TableCell align="right" isNumeric>
                      <MaskedField value={exp.amount} maskType="currency" />
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          exp.approval_status === 'APPROVED'
                            ? 'verified'
                            : exp.approval_status === 'REJECTED'
                            ? 'danger'
                            : 'warning'
                        }
                        size="sm"
                      >
                        {exp.approval_status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-text-muted font-mono">
                        {exp.reimbursement_status}
                      </span>
                    </TableCell>
                    <TableCell align="right">
                      {isFinanceOrOwner &&
                        exp.is_out_of_pocket &&
                        exp.approval_status === 'APPROVED' &&
                        exp.reimbursement_status === 'DUE' && (
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setSettleTargetTx(exp);
                              setIsSettleModalOpen(true);
                            }}
                          >
                            Settle UTR
                          </Button>
                        )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* MODAL 1: Record Site Expense */}
      <Modal
        isOpen={isExpenseModalOpen}
        onClose={() => setIsExpenseModalOpen(false)}
        title="Record Site Cash Expense"
        description="Enter voucher details for fuel, machine spares, or emergency site supplies."
        maxWidth="lg"
      >
        <form onSubmit={handleExpenseSubmit} className="space-y-4">
          {duplicateWarning && (
            <div className="rounded-md bg-status-warning-soft p-3 border border-status-warning/20 text-xs text-status-warning">
              {duplicateWarning}
            </div>
          )}

          {deficitCapWarning && (
            <div
              className={`rounded-md p-3 border text-xs ${
                deficitCapWarning.isExceeded
                  ? 'bg-status-danger-soft border-status-danger/20 text-status-danger'
                  : 'bg-status-warning-soft border-status-warning/20 text-status-warning'
              }`}
            >
              {deficitCapWarning.message}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Expense Amount (₹)"
              type="number"
              step="1"
              required
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="e.g. 1500"
            />

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-text-muted mb-1.5">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-surface-sunk border border-border rounded-md text-xs sm:text-sm py-2 px-3 text-text focus:outline-none focus:border-accent"
              >
                <option value="DIESEL">Emergency Diesel</option>
                <option value="SPARES">Rig & Plant Spares</option>
                <option value="FOOD_WATER">Crew Refreshments / Water</option>
                <option value="TRANSPORT">Local Transport / Courier</option>
                <option value="TOOLS">Welding & Tools</option>
                <option value="SAFETY">Safety Gear</option>
              </select>
            </div>
          </div>

          <Input
            label="Voucher Description / Vendor Note"
            required
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. 15 liters diesel for standby DG set"
          />

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Expense Date"
              type="date"
              value={expenseDate}
              onChange={(e) => setExpenseDate(e.target.value)}
            />

            <div className="flex items-center gap-4 pt-6">
              <label className="flex items-center gap-2 text-xs font-medium text-text cursor-pointer">
                <input
                  type="checkbox"
                  checked={isOutOfPocket}
                  onChange={(e) => setIsOutOfPocket(e.target.checked)}
                  className="rounded border-border text-accent focus:ring-accent"
                />
                <span>Supervisor Paid Out-of-Pocket</span>
              </label>

              <label className="flex items-center gap-2 text-xs font-medium text-text cursor-pointer">
                <input
                  type="checkbox"
                  checked={hasPhysicalBill}
                  onChange={(e) => setHasPhysicalBill(e.target.checked)}
                  className="rounded border-border text-accent focus:ring-accent"
                />
                <span>Physical Bill Present</span>
              </label>
            </div>
          </div>

          {/* Photo upload */}
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-text-muted mb-1.5">
              Voucher Slip / Receipt Photograph
            </label>
            <div className="flex items-center gap-3">
              <label className="cursor-pointer">
                <span className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-pill bg-surface-sunk border border-border text-text hover:bg-surface transition-colors">
                  <Camera className="h-3.5 w-3.5" />
                  <span>Attach Bill Photo</span>
                </span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                  className="hidden"
                />
              </label>
              {isCompressing && (
                <span className="text-xs text-accent">Compressing bill image...</span>
              )}
              {receiptPhoto && (
                <span className="text-xs text-status-success font-medium">
                  Attached: {receiptPhoto.name}
                </span>
              )}
            </div>
          </div>

          <div className="flex justify-end gap-2.5 pt-3 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setIsExpenseModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSubmitting}
            >
              Record Voucher
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 2: Settle Reimbursement UTR */}
      <Modal
        isOpen={isSettleModalOpen}
        onClose={() => setIsSettleModalOpen(false)}
        title="Settle Reimbursement Disbursement"
        description="Record banking transaction reference (UTR) for supervisor out-of-pocket payout."
        maxWidth="md"
      >
        <form onSubmit={handleSettleReimbursement} className="space-y-4">
          <div className="p-3 bg-surface-sunk/60 rounded-md border border-border space-y-1 text-xs">
            <div className="text-text-muted">Target Voucher: #{settleTargetTx?.id}</div>
            <div className="text-text-muted font-mono">{settleTargetTx?.description}</div>
            <div className="font-semibold text-text font-mono text-sm pt-1">
              Amount Due: ₹{settleTargetTx?.amount.toLocaleString('en-IN')}
            </div>
          </div>

          <Input
            label="Bank UTR / IMPS Reference Number"
            required
            value={settleUtrRef}
            onChange={(e) => setSettleUtrRef(e.target.value)}
            placeholder="e.g. HDFC0001239845"
          />

          <div className="flex justify-end gap-2.5 pt-3 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setIsSettleModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSubmitting}
            >
              Mark Settled
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 3: Replenish Wallet Float */}
      <Modal
        isOpen={isReplenishModalOpen}
        onClose={() => setIsReplenishModalOpen(false)}
        title="Replenish Site Float"
        description="Transfer commercial operating capital into Site Office Petty Cash Float."
        maxWidth="md"
      >
        <form onSubmit={handleReplenishSubmit} className="space-y-4">
          <Input
            label="Replenishment Amount (₹)"
            type="number"
            required
            value={replenishAmount}
            onChange={(e) => setReplenishAmount(e.target.value)}
          />

          <Input
            label="Accounting Ledger Note"
            value={replenishDesc}
            onChange={(e) => setReplenishDesc(e.target.value)}
          />

          <div className="flex justify-end gap-2.5 pt-3 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setIsReplenishModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSubmitting}
            >
              Disburse Float
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 4: Out-of-Pocket Claim */}
      <Modal
        isOpen={isReimburseModalOpen}
        onClose={() => setIsReimburseModalOpen(false)}
        title="Claim Supervisor Out-of-Pocket Deficit"
        description="Submit outstanding site deficit for commercial accounting review."
        maxWidth="md"
      >
        <form onSubmit={handleReimburseSubmit} className="space-y-4">
          <div className="p-3 bg-surface-sunk/60 rounded-md border border-border text-xs space-y-1">
            <span className="text-text-muted">Total Outstanding Deficit:</span>
            <div className="text-base font-semibold text-status-warning font-mono">
              ₹{supervisorDeficit.toLocaleString('en-IN')}
            </div>
          </div>

          <Input
            label="Claim Amount (₹)"
            type="number"
            required
            value={reimburseAmount}
            onChange={(e) => setReimburseAmount(e.target.value)}
          />

          <Input
            label="Supervisor Bank Account Note"
            placeholder="e.g. Axis Bank A/C ending in 4102"
            value={reimburseRef}
            onChange={(e) => setReimburseRef(e.target.value)}
          />

          <div className="flex justify-end gap-2.5 pt-3 border-t border-border">
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => setIsReimburseModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isSubmitting}
            >
              Submit Claim
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL 5: Receipt Bill Inspection */}
      <Modal
        isOpen={Boolean(receiptModalUrl)}
        onClose={() => setReceiptModalUrl(null)}
        title="Physical Bill Voucher Inspection"
        description="Encrypted cryptographic image artifact stored for commercial audit."
        maxWidth="lg"
      >
        <div className="space-y-4">
          <div className="h-64 sm:h-80 w-full rounded-md bg-surface-sunk flex items-center justify-center border border-border overflow-hidden">
            <div className="text-center p-6 space-y-2">
              <Receipt className="h-10 w-10 text-accent mx-auto" />
              <div className="font-semibold text-text text-sm">Physical Tax Invoice #4819</div>
              <p className="text-xs text-text-muted max-w-xs">
                M/s Malabar Diesel Spares & Hydraulics, Vadakara Bypass. Verified by Site Engineer.
              </p>
            </div>
          </div>

          <div className="flex justify-end">
            <Button
              variant="secondary"
              size="md"
              onClick={() => setReceiptModalUrl(null)}
            >
              Close Inspection
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
