'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import apiClient, { isOfflineQueued, getApiBaseUrl } from '@/lib/api-client';
import { compressImage, fileToDataUrl, formatFileSize } from '@/lib/image-compression';
import { useAuth } from '@/lib/auth-context';
import {
  Wallet,
  PlusCircle,
  Download,
  AlertTriangle,
  CheckCircle2,
  Receipt,
  AlertCircle,
  X,
  Camera,
  Trash2,
  TrendingDown,
  RefreshCw,
  CloudOff,
  ShieldCheck,
  Check,
  Ban,
  ArrowUpRight,
  Layers,
  FileCheck,
} from 'lucide-react';

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

const INITIAL_EXPENSES: ExpenseItem[] = [
  {
    id: 1,
    amount: 3200,
    category: 'DIESEL',
    description: 'Emergency diesel for generator standby (35 liters)',
    date: new Date().toISOString().split('T')[0],
    is_out_of_pocket: false,
    approval_status: 'APPROVED',
    reimbursement_status: 'NOT_APPLICABLE',
    has_physical_bill: true,
  },
  {
    id: 2,
    amount: 1450,
    category: 'SPARES',
    description: 'Bauer rig hydraulic seals and replacement O-rings',
    date: new Date(Date.now() - 86400000).toISOString().split('T')[0],
    is_out_of_pocket: true,
    approval_status: 'PENDING',
    reimbursement_status: 'DUE',
    has_physical_bill: true,
  },
  {
    id: 3,
    amount: 850,
    category: 'FOOD_WATER',
    description: 'Night shift refreshment & drinking water cans for piling crew',
    date: new Date(Date.now() - 172800000).toISOString().split('T')[0],
    is_out_of_pocket: false,
    approval_status: 'APPROVED',
    reimbursement_status: 'NOT_APPLICABLE',
    has_physical_bill: false,
  },
  {
    id: 4,
    amount: 600,
    category: 'TRANSPORT',
    description: 'Auto-rickshaw courier charges for soil sample lab testing',
    date: new Date(Date.now() - 259200000).toISOString().split('T')[0],
    is_out_of_pocket: true,
    approval_status: 'APPROVED',
    reimbursement_status: 'DUE',
    has_physical_bill: true,
  },
  {
    id: 5,
    amount: 2200,
    category: 'TOOLS',
    description: 'Gas cutting nozzles & grinding discs for cage welding',
    date: new Date(Date.now() - 345600000).toISOString().split('T')[0],
    is_out_of_pocket: true,
    approval_status: 'PENDING',
    reimbursement_status: 'DUE',
    has_physical_bill: true,
  },
];

export default function PettyCashPage() {
  const { user } = useAuth();
  const [siteId] = useState('1');
  const [walletBalance, setWalletBalance] = useState(14500.0);
  const [supervisorDeficit, setSupervisorDeficit] = useState(2050.0);
  const [expenses, setExpenses] = useState<ExpenseItem[]>(INITIAL_EXPENSES);
  const [isLoadingWallet, setIsLoadingWallet] = useState(false);

  // Role Differentiation Flags
  const isFinanceOrOwner = user?.role === 'FINANCE_HEAD' || user?.role === 'OWNER';
  const isSupervisorOrEngineer = user?.role === 'SUPERVISOR' || user?.role === 'SITE_ENGINEER';

  // Active Tab
  const [activeTab, setActiveTab] = useState<'approvals' | 'ledger' | 'entry'>(
    user?.role === 'FINANCE_HEAD' ? 'approvals' : 'ledger'
  );

  useEffect(() => {
    if (user?.role === 'FINANCE_HEAD') {
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

  // Form State
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState('FUEL');
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
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'offline' | 'error'; text: string } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [filterCategory, setFilterCategory] = useState<string>('ALL');

  // Fetch live wallet balance from backend if available
  const fetchWallet = useCallback(async () => {
    setIsLoadingWallet(true);
    try {
      const res = await apiClient.get(`/petty-cash/wallet/${siteId}`);
      if (res.data) {
        setWalletBalance(res.data.current_balance ?? 0);
        setSupervisorDeficit(res.data.supervisor_deficit ?? 0);
      }
    } catch {
      // Backend may not be reachable in pure offline mode
    } finally {
      setIsLoadingWallet(false);
    }
  }, [siteId]);

  useEffect(() => {
    fetchWallet();
  }, [fetchWallet]);

  // Duplicate check logic (Vulnerability 4)
  const duplicateWarning = useMemo(() => {
    const numAmount = parseFloat(amount);
    if (!numAmount || isNaN(numAmount)) return null;

    const matched = expenses.find((exp) => {
      const diffAmount = Math.abs(exp.amount - numAmount);
      return diffAmount < 0.01 && exp.category === category;
    });

    if (matched) {
      return `Potential duplicate detected! An expense of ₹${matched.amount.toLocaleString()} in category ${matched.category} was already recorded on ${matched.date} (${matched.description}).`;
    }
    return null;
  }, [amount, category, expenses]);

  // Deficit Cap check (Vulnerability 5 - ₹50k Cap)
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
        message: `Strict Deficit Cap Exceeded: Projected out-of-pocket deficit ₹${projectedDeficit.toLocaleString()} exceeds the maximum ₹50,000 threshold. Submission will be rejected by AnomalyDetector.`,
      };
    } else if (projectedDeficit > 40000) {
      return {
        isExceeded: false,
        message: `High Deficit Warning: Projected deficit is ₹${projectedDeficit.toLocaleString()} (₹${(50000 - projectedDeficit).toLocaleString()} remaining before ₹50,000 hard cap).`,
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
        text: `Expense of ₹${numAmount.toLocaleString()} recorded successfully!`,
      });
      setIsExpenseModalOpen(false);
      resetExpenseForm();
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        const queuedTx: ExpenseItem = {
          id: 'offline-' + Date.now(),
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
          type: 'offline',
          text: `Expense of ₹${numAmount.toLocaleString()} saved offline! Queued for sync when online.`,
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
        text: `Reimbursement request of ₹${reimbAmt.toLocaleString()} submitted!`,
      });
      setIsReimburseModalOpen(false);
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        setToastMessage({
          type: 'offline',
          text: `Reimbursement request of ₹${reimbAmt.toLocaleString()} queued offline for sync.`,
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
        text: `Reimbursement of ₹${settleTargetTx.amount.toLocaleString()} settled with UTR: ${settleUtrRef}`,
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
        text: `Site Petty Cash Wallet replenished with ₹${amt.toLocaleString()}!`,
      });
      setIsReplenishModalOpen(false);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setToastMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to replenish wallet.' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Tally XML Export Download
  const handleTallyExport = async () => {
    try {
      const baseURL = getApiBaseUrl();
      const url = `${baseURL}/petty-cash/tally-export?site_id=${siteId}&format=xml`;
      const token = localStorage.getItem('token');
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(url, { headers });
      if (!res.ok) throw new Error('Export request failed');
      const xmlData = await res.text();

      const blob = new Blob([xmlData], { type: 'application/xml' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `Tally_PettyCash_Site${siteId}_${new Date().toISOString().split('T')[0]}.xml`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setToastMessage({
        type: 'success',
        text: 'Tally Prime XML vouchers successfully exported!',
      });
    } catch {
      // Fallback local XML generator
      const vouchersXml = expenses
        .map(
          (t) => `    <VOUCHER VCHTYPE="Payment" ACTION="Create">
      <DATE>${t.date.replace(/-/g, '')}</DATE>
      <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
      <NARRATION>${t.description.replace(/&/g, '&amp;')}</NARRATION>
      <ALLLEDGERENTRIES.LIST>
        <LEDGERNAME>${t.category}</LEDGERNAME>
        <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
        <AMOUNT>-${t.amount.toFixed(2)}</AMOUNT>
      </ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST>
        <LEDGERNAME>Petty Cash</LEDGERNAME>
        <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
        <AMOUNT>${t.amount.toFixed(2)}</AMOUNT>
      </ALLLEDGERENTRIES.LIST>
    </VOUCHER>`
        )
        .join('\n');

      const fullXml = `<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC><REPORTNAME>All Masters</REPORTNAME></REQUESTDESC>
      <REQUESTDATA>
${vouchersXml}
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>`;

      const blob = new Blob([fullXml], { type: 'application/xml' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = `Tally_PettyCash_Site${siteId}_${new Date().toISOString().split('T')[0]}.xml`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setToastMessage({
        type: 'success',
        text: 'Tally Prime XML vouchers generated and downloaded!',
      });
    }
  };

  const pendingExpenses = useMemo(() => {
    return expenses.filter((e) => e.approval_status === 'PENDING');
  }, [expenses]);

  const dueReimbursements = useMemo(() => {
    return expenses.filter((e) => e.is_out_of_pocket && e.reimbursement_status === 'DUE');
  }, [expenses]);

  const filteredExpenses = useMemo(() => {
    if (filterCategory === 'ALL') return expenses;
    return expenses.filter((e) => e.category === filterCategory);
  }, [expenses, filterCategory]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-gray-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
              <Wallet className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Petty Cash & Disbursements</h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-700 border">
                  {user?.role?.replace('_', ' ') || 'Site Wallet'}
                </span>
              </div>
              <p className="text-xs sm:text-sm text-gray-500">
                {isFinanceOrOwner
                  ? 'Commercial Controller Hub: Approve vouchers, settle claims, and export to Tally'
                  : 'Site Operations: Log emergency cash spends and track out-of-pocket claims'}
              </p>
            </div>
          </div>
        </div>

        {/* Action Controls - Dynamic by Role */}
        <div className="flex flex-wrap items-center gap-2">
          {isFinanceOrOwner && (
            <>
              <button
                type="button"
                onClick={handleTallyExport}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-xs font-semibold text-gray-700 shadow-xs hover:bg-gray-50 transition-colors cursor-pointer"
              >
                <Download className="h-3.5 w-3.5 text-gray-500" />
                <span>Export Tally XML</span>
              </button>

              <button
                type="button"
                onClick={() => setIsReplenishModalOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-3.5 py-2 text-xs font-semibold text-emerald-700 shadow-xs hover:bg-emerald-100 transition-colors cursor-pointer"
              >
                <ArrowUpRight className="h-3.5 w-3.5 text-emerald-600" />
                <span>Replenish Wallet</span>
              </button>
            </>
          )}

          {isSupervisorOrEngineer && (
            <button
              type="button"
              onClick={() => setIsReimburseModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-700 shadow-xs hover:bg-indigo-100 transition-colors cursor-pointer"
            >
              <Receipt className="h-3.5 w-3.5 text-indigo-600" />
              <span>Claim Reimbursement</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsExpenseModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-emerald-500 transition-colors cursor-pointer"
          >
            <PlusCircle className="h-3.5 w-3.5" />
            <span>{isFinanceOrOwner ? 'Log Voucher' : 'Log New Expense'}</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {toastMessage && (
        <div
          className={`rounded-lg p-4 border flex items-start gap-3 shadow-xs ${
            toastMessage.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-900'
              : toastMessage.type === 'offline'
              ? 'bg-amber-50 border-amber-200 text-amber-900'
              : 'bg-red-50 border-red-200 text-red-900'
          }`}
        >
          {toastMessage.type === 'success' && <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />}
          {toastMessage.type === 'offline' && <CloudOff className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />}
          {toastMessage.type === 'error' && <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />}
          <div className="flex-1 text-xs font-medium">{toastMessage.text}</div>
          <button onClick={() => setToastMessage(null)} className="text-xs font-semibold hover:underline cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Wallet Balance */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Site Wallet Balance</span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={fetchWallet}
                disabled={isLoadingWallet}
                title="Refresh wallet balance"
                className="p-1 rounded-md text-emerald-600 hover:bg-emerald-50 cursor-pointer"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isLoadingWallet ? 'animate-spin' : ''}`} />
              </button>
              <span className="p-1.5 bg-emerald-50 text-emerald-600 rounded-md">
                <Wallet className="h-4 w-4" />
              </span>
            </div>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-emerald-600">
            ₹{walletBalance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <p className="mt-1 text-[11px] text-gray-500">Available cash in site office drawer</p>
        </div>

        {/* Supervisor Deficit */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Out-of-Pocket Due</span>
            <span className="p-1.5 bg-amber-50 text-amber-600 rounded-md">
              <TrendingDown className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-amber-600">
            ₹{supervisorDeficit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] text-gray-500">
            <span>Spent from personal funds</span>
            <span className="text-amber-700 font-medium">• {dueReimbursements.length} pending settlement</span>
          </div>
        </div>

        {/* Cap Limit */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">₹50k Deficit Safety Headroom</span>
            <span className={`p-1.5 rounded-md ${supervisorDeficit > 40000 ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>
              <AlertTriangle className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-gray-900">
            ₹{Math.max(0, 50000 - supervisorDeficit).toLocaleString('en-IN')}
          </div>
          <div className="mt-2 w-full bg-gray-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${supervisorDeficit > 40000 ? 'bg-red-500' : 'bg-indigo-500'}`}
              style={{ width: `${Math.min(100, (supervisorDeficit / 50000) * 100)}%` }}
            />
          </div>
          <p className="mt-1 text-[11px] text-gray-400">Enforced by backend RBAC & deficit anomaly checks</p>
        </div>
      </div>

      {/* Role-Specific Workspace Navigation Tabs */}
      <div className="flex border-b border-gray-200 bg-white px-4 rounded-t-xl">
        {isFinanceOrOwner && (
          <button
            onClick={() => setActiveTab('approvals')}
            className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-bold transition-colors cursor-pointer ${
              activeTab === 'approvals'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <ShieldCheck className="h-4 w-4" />
            <span>Approval & Settlement Queue</span>
            {pendingExpenses.length > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-100 text-amber-800 font-bold">
                {pendingExpenses.length}
              </span>
            )}
          </button>
        )}

        <button
          onClick={() => setActiveTab('ledger')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-bold transition-colors cursor-pointer ${
            activeTab === 'ledger'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Layers className="h-4 w-4" />
          <span>{isSupervisorOrEngineer ? 'My Claims History' : 'Complete Ledger'}</span>
        </button>

        {isSupervisorOrEngineer && (
          <button
            onClick={() => setActiveTab('entry')}
            className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-bold transition-colors cursor-pointer ${
              activeTab === 'entry'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <PlusCircle className="h-4 w-4" />
            <span>Submit Site Expense</span>
          </button>
        )}
      </div>

      {/* TAB 1: Finance Approval & Settlement Queue (Visible to Finance Head & Owner) */}
      {isFinanceOrOwner && activeTab === 'approvals' && (
        <div className="space-y-6">
          {/* Pending Approval Section */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <span>Pending Expense Approvals</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
                    {pendingExpenses.length} awaiting review
                  </span>
                </h2>
                <p className="text-xs text-gray-500">Review field vouchers submitted by Site Engineers and Supervisors</p>
              </div>
            </div>

            {pendingExpenses.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-xs">
                <FileCheck className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                <p className="font-semibold text-gray-800">All expenses are reviewed!</p>
                <p className="text-gray-400 mt-0.5">No pending claims in the queue for this site.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
                  <thead className="bg-gray-50 text-gray-500 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Date</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3 text-right">Amount (₹)</th>
                      <th className="px-4 py-3 text-center">Out-of-Pocket</th>
                      <th className="px-4 py-3 text-center">Physical Bill</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {pendingExpenses.map((tx) => (
                      <tr key={tx.id} className="hover:bg-gray-50/70 transition-colors">
                        <td className="px-4 py-3 font-medium text-gray-700 whitespace-nowrap">{tx.date}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-800">
                            {tx.category}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">{tx.description}</td>
                        <td className="px-4 py-3 text-right font-bold text-gray-900 whitespace-nowrap">
                          ₹{tx.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {tx.is_out_of_pocket ? (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                              Yes (Supervisor)
                            </span>
                          ) : (
                            <span className="text-gray-400">Site Drawer</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {tx.has_physical_bill ? (
                            <span className="text-emerald-700 font-semibold flex items-center justify-center gap-1">
                              <CheckCircle2 className="h-3.5 w-3.5" />
                              Attached
                            </span>
                          ) : (
                            <span className="text-amber-600 font-semibold">No Bill</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => handleApproveExpense(tx.id)}
                              title="Approve Expense Voucher"
                              className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-600 text-white rounded text-xs font-bold hover:bg-emerald-700 transition-colors cursor-pointer"
                            >
                              <Check className="h-3 w-3" />
                              <span>Approve</span>
                            </button>
                            <button
                              onClick={() => handleRejectExpense(tx.id)}
                              title="Reject Voucher"
                              className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-700 border border-red-200 rounded text-xs font-bold hover:bg-red-100 transition-colors cursor-pointer"
                            >
                              <Ban className="h-3 w-3" />
                              <span>Reject</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Out-of-Pocket Reimbursements Settlement Section */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                  <span>Reimbursements Settlement Queue</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                    {dueReimbursements.length} due payment
                  </span>
                </h2>
                <p className="text-xs text-gray-500">Disburse approved out-of-pocket claims back to field supervisors</p>
              </div>
            </div>

            {dueReimbursements.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-xs">
                <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                <p className="font-semibold text-gray-800">All reimbursements settled!</p>
                <p className="text-gray-400 mt-0.5">No supervisor is owed funds currently.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
                  <thead className="bg-gray-50 text-gray-500 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Expense ID</th>
                      <th className="px-4 py-3">Date</th>
                      <th className="px-4 py-3">Description</th>
                      <th className="px-4 py-3 text-right">Amount (₹)</th>
                      <th className="px-4 py-3 text-center">Approval</th>
                      <th className="px-4 py-3 text-right">Settlement Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 bg-white">
                    {dueReimbursements.map((tx) => (
                      <tr key={tx.id} className="hover:bg-gray-50/70 transition-colors">
                        <td className="px-4 py-3 font-semibold text-gray-900">#{tx.id}</td>
                        <td className="px-4 py-3 text-gray-700">{tx.date}</td>
                        <td className="px-4 py-3 font-medium text-gray-900 max-w-sm truncate">{tx.description}</td>
                        <td className="px-4 py-3 text-right font-bold text-amber-700">
                          ₹{tx.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              tx.approval_status === 'APPROVED'
                                ? 'bg-emerald-50 text-emerald-700'
                                : 'bg-amber-50 text-amber-700'
                            }`}
                          >
                            {tx.approval_status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right whitespace-nowrap">
                          <button
                            onClick={() => {
                              setSettleTargetTx(tx);
                              setSettleUtrRef(`NEFT-${Date.now().toString().slice(-6)}`);
                              setIsSettleModalOpen(true);
                            }}
                            className="inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white rounded text-xs font-bold hover:bg-indigo-700 transition-colors cursor-pointer"
                          >
                            <Receipt className="h-3 w-3" />
                            <span>Settle & Pay</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Complete Ledger & History */}
      {activeTab === 'ledger' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-gray-900">Site Expense Ledger</h2>
              <p className="text-xs text-gray-500">Audit trail of all recorded petty cash transactions</p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Category:</span>
              <select
                value={filterCategory}
                onChange={(e) => setFilterCategory(e.target.value)}
                aria-label="Filter expenses by category"
                className="rounded-lg border border-gray-300 px-2.5 py-1 text-xs shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="ALL">All Categories</option>
                <option value="DIESEL">Diesel</option>
                <option value="SPARES">Spares & Seals</option>
                <option value="FOOD_WATER">Food & Water</option>
                <option value="TRANSPORT">Transport</option>
                <option value="LABOUR">Direct Labour</option>
                <option value="TOOLS">Tools & Hardware</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3 text-right">Amount (₹)</th>
                  <th className="px-4 py-3 text-center">Type</th>
                  <th className="px-4 py-3 text-center">Approval</th>
                  <th className="px-4 py-3 text-center">Reimbursement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {filteredExpenses.map((tx) => (
                  <tr key={tx.id} className="hover:bg-gray-50/70 transition-colors">
                    <td className="px-4 py-3 text-gray-700 whitespace-nowrap font-medium">{tx.date}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-800">
                        {tx.category}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900 max-w-sm truncate">{tx.description}</td>
                    <td className="px-4 py-3 text-right font-bold text-gray-900 whitespace-nowrap">
                      ₹{tx.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 text-center whitespace-nowrap">
                      {tx.is_out_of_pocket ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                          Out-of-Pocket
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-gray-100 text-gray-700">
                          Site Wallet
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center whitespace-nowrap">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          tx.approval_status === 'APPROVED'
                            ? 'bg-emerald-50 text-emerald-700'
                            : tx.approval_status === 'REJECTED'
                            ? 'bg-red-50 text-red-700'
                            : 'bg-amber-50 text-amber-700'
                        }`}
                      >
                        {tx.approval_status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center whitespace-nowrap">
                      {tx.reimbursement_status === 'SETTLED' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Settled
                        </span>
                      ) : tx.reimbursement_status === 'DUE' ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                          Due
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: Inline Submit Expense Voucher (For Supervisor / Site Engineer) */}
      {isSupervisorOrEngineer && activeTab === 'entry' && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs max-w-3xl mx-auto">
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
            <Receipt className="h-5 w-5 text-indigo-600" />
            <h2 className="text-base font-bold text-gray-900">Submit Site Expense Voucher</h2>
          </div>

          <form onSubmit={handleExpenseSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700">Amount (₹) *</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  placeholder="e.g. 1500"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Category *</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="FUEL">Diesel & Generator Fuel</option>
                  <option value="TOOLS">Rig Spares & Consumables</option>
                  <option value="WELDING_REPAIR">Hardware, Gas & Welding</option>
                  <option value="FOOD_WATER">Crew Refreshments & Water</option>
                  <option value="TRANSPORT">Local Transport & Courier</option>
                  <option value="OTHER">Other Emergency Site Expense</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Quantity (Optional)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="e.g. 25"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Unit</label>
                <select
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                >
                  <option value="Liters">Liters</option>
                  <option value="Nos">Nos / Units</option>
                  <option value="Kg">Kg</option>
                  <option value="Bags">Bags</option>
                  <option value="Trips">Trips</option>
                </select>
              </div>
            </div>

            {duplicateWarning && (
              <div className="rounded-lg bg-amber-50 p-3 border border-amber-200 text-xs text-amber-800 flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                <span>{duplicateWarning}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-gray-700">Description & Purpose *</label>
              <textarea
                required
                rows={2}
                placeholder="What was purchased and for which rig/pier operation?"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700">Expense Date</label>
                <input
                  type="date"
                  value={expenseDate}
                  onChange={(e) => setExpenseDate(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                />
              </div>

              <div className="flex flex-col justify-center space-y-2 pt-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isOutOfPocket}
                    onChange={(e) => setIsOutOfPocket(e.target.checked)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-xs font-semibold text-gray-800">
                    Paid from personal pocket (Request Reimbursement)
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasPhysicalBill}
                    onChange={(e) => setHasPhysicalBill(e.target.checked)}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-xs font-semibold text-gray-800">Physical Bill / Cash Receipt in Hand</span>
                </label>
              </div>
            </div>

            {/* Bill Receipt Upload */}
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Upload Bill Photo / Camera Capture</label>
              <div className="flex items-center gap-3">
                <label className="inline-flex items-center gap-1.5 px-3.5 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50 cursor-pointer shadow-xs">
                  <Camera className="h-4 w-4 text-gray-500" />
                  <span>Choose or Capture Bill</span>
                  <input type="file" accept="image/*" onChange={handlePhotoUpload} className="hidden" />
                </label>
                {isCompressing && <span className="text-xs text-indigo-600 animate-pulse">Compressing photo...</span>}
              </div>
              {receiptPhoto && (
                <div className="mt-2 flex items-center justify-between p-2 rounded-lg border border-gray-200 bg-gray-50 text-xs">
                  <span className="truncate max-w-xs font-medium text-gray-700">{receiptPhoto.name}</span>
                  <span className="text-gray-500 text-[11px]">{formatFileSize(receiptPhoto.compressedSize)}</span>
                  <button
                    type="button"
                    onClick={() => setReceiptPhoto(null)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-gray-100 flex justify-end">
              <button
                type="submit"
                disabled={isSubmitting || Boolean(deficitCapWarning?.isExceeded)}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-6 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors cursor-pointer"
              >
                <PlusCircle className="h-4 w-4" />
                <span>{isSubmitting ? 'Submitting...' : 'Submit Claim Voucher'}</span>
              </button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL 1: Settle Reimbursement Modal (Finance Only) */}
      {isSettleModalOpen && settleTargetTx && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-gray-900/60 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-2">
                <Receipt className="h-5 w-5 text-indigo-600" />
                <h3 className="text-base font-bold text-gray-900">Settle Out-of-Pocket Claim</h3>
              </div>
              <button onClick={() => setIsSettleModalOpen(false)} className="p-1 text-gray-400 hover:text-gray-600 rounded-lg cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSettleReimbursement} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase">Expense Item</label>
                <div className="text-sm font-bold text-gray-900 mt-0.5">{settleTargetTx.description}</div>
                <div className="text-lg font-bold text-emerald-600 mt-1">₹{settleTargetTx.amount.toLocaleString()}</div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Bank NEFT / UPI Reference *</label>
                <input
                  type="text"
                  required
                  value={settleUtrRef}
                  onChange={(e) => setSettleUtrRef(e.target.value)}
                  placeholder="e.g. UTR-988410294"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs focus:ring-1 focus:ring-indigo-500 font-medium"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsSettleModalOpen(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-indigo-500 transition-colors cursor-pointer"
                >
                  {isSubmitting ? 'Settling...' : 'Confirm Settlement'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Replenish Wallet Modal (Finance Only) */}
      {isReplenishModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-gray-900/60 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-2">
                <ArrowUpRight className="h-5 w-5 text-emerald-600" />
                <h3 className="text-base font-bold text-gray-900">Replenish Site Petty Cash Wallet</h3>
              </div>
              <button onClick={() => setIsReplenishModalOpen(false)} className="p-1 text-gray-400 hover:text-gray-600 rounded-lg cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleReplenishSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700">Replenishment Amount (₹) *</label>
                <input
                  type="number"
                  step="100"
                  required
                  value={replenishAmount}
                  onChange={(e) => setReplenishAmount(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs font-bold text-emerald-700"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Remarks / Transfer Details</label>
                <input
                  type="text"
                  value={replenishDesc}
                  onChange={(e) => setReplenishDesc(e.target.value)}
                  placeholder="e.g. Bank cash withdrawal ref #9932"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsReplenishModalOpen(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-emerald-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-500 transition-colors cursor-pointer"
                >
                  {isSubmitting ? 'Transferring...' : 'Transfer to Wallet'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Supervisor Claim Modal */}
      {isReimburseModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-gray-900/60 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-2">
                <Receipt className="h-5 w-5 text-indigo-600" />
                <h3 className="text-base font-bold text-gray-900">Claim Reimbursement</h3>
              </div>
              <button onClick={() => setIsReimburseModalOpen(false)} className="p-1 text-gray-400 hover:text-gray-600 rounded-lg cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleReimburseSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700">Total Out-of-Pocket Deficit</label>
                <div className="mt-1 text-2xl font-bold text-amber-600">
                  ₹{supervisorDeficit.toLocaleString('en-IN')}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Claim Amount (₹) *</label>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={reimburseAmount}
                  onChange={(e) => setReimburseAmount(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs font-bold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Reimbursement Reference No.</label>
                <input
                  type="text"
                  value={reimburseRef}
                  onChange={(e) => setReimburseRef(e.target.value)}
                  placeholder="e.g. CLAIM-SEPT-WEEK3"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsReimburseModalOpen(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-xs hover:bg-indigo-500 transition-colors cursor-pointer"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Claim'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: Log Expense Modal */}
      {isExpenseModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-gray-900/60 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-2">
                <PlusCircle className="h-5 w-5 text-emerald-600" />
                <h3 className="text-base font-bold text-gray-900">Record Petty Cash Expense</h3>
              </div>
              <button onClick={() => setIsExpenseModalOpen(false)} className="p-1 text-gray-400 hover:text-gray-600 rounded-lg cursor-pointer">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleExpenseSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700">Amount (₹) *</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="e.g. 1500"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs font-semibold"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700">Category *</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                  >
                    <option value="DIESEL">Diesel</option>
                    <option value="SPARES">Spares & Seals</option>
                    <option value="FOOD_WATER">Food & Water</option>
                    <option value="TRANSPORT">Transport</option>
                    <option value="TOOLS">Tools & Hardware</option>
                    <option value="OTHER">Other Expense</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Description *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rig hydraulic O-rings"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700">Date</label>
                  <input
                    type="date"
                    value={expenseDate}
                    onChange={(e) => setExpenseDate(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                  />
                </div>

                <div className="flex flex-col justify-center space-y-1">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isOutOfPocket}
                      onChange={(e) => setIsOutOfPocket(e.target.checked)}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-xs font-semibold text-gray-800">Paid Out-of-Pocket</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={hasPhysicalBill}
                      onChange={(e) => setHasPhysicalBill(e.target.checked)}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-xs font-semibold text-gray-800">Has Physical Bill</span>
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsExpenseModalOpen(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || Boolean(deficitCapWarning?.isExceeded)}
                  className="rounded-lg bg-emerald-600 px-5 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-500 transition-colors cursor-pointer"
                >
                  {isSubmitting ? 'Recording...' : 'Record Expense'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
