'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import apiClient, { isOfflineQueued } from '@/lib/api-client';
import { compressImage, fileToDataUrl, formatFileSize } from '@/lib/image-compression';
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
];

export default function PettyCashPage() {
  const [siteId] = useState('1');
  const [walletBalance, setWalletBalance] = useState(14500.0);
  const [supervisorDeficit, setSupervisorDeficit] = useState(2050.0);
  const [expenses, setExpenses] = useState<ExpenseItem[]>(INITIAL_EXPENSES);
  const [isLoadingWallet, setIsLoadingWallet] = useState(false);

  // Modals
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  const [isReimburseModalOpen, setIsReimburseModalOpen] = useState(false);

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
      // Backend may not be running in testing mode; maintain default state
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
      quantity: quantity ? parseFloat(quantity) : undefined,
      unit: quantity ? unit : undefined,
      has_physical_bill: hasPhysicalBill,
      receipt_photo_url: receiptPhoto?.dataUrl || undefined,
      date: expenseDate,
    };

    try {
      const res = await apiClient.post('/petty-cash/expenses', payload);
      const newTx: ExpenseItem = res.data || {
        id: 'tx-' + Date.now(),
        amount: numAmount,
        category,
        description,
        date: expenseDate,
        is_out_of_pocket: isOutOfPocket,
        approval_status: 'PENDING',
        reimbursement_status: isOutOfPocket ? 'DUE' : 'NOT_APPLICABLE',
        has_physical_bill: hasPhysicalBill,
      };

      setExpenses((prev) => [newTx, ...prev]);

      // Optimistic balance update
      if (isOutOfPocket) {
        setSupervisorDeficit((prev) => prev + numAmount);
      } else {
        setWalletBalance((prev) => prev - numAmount);
      }

      setToastMessage({
        type: 'success',
        text: `Expense of ₹${numAmount.toLocaleString()} logged successfully!`,
      });
      setIsExpenseModalOpen(false);
      resetExpenseForm();
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        // Save optimistically in UI list for offline experience
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

  // Tally XML Export Download
  const handleTallyExport = async () => {
    try {
      const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const url = `${baseURL}/petty-cash/tally-export?site_id=${siteId}&format=xml`;
      const token = localStorage.getItem('token');
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(url, { headers });
      if (!res.ok) throw new Error('Export request failed');
      const xmlData = await res.text();

      // Trigger client-side file download
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
      // Fallback: Generate valid local Tally XML voucher payload for the supervisor
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

  const filteredExpenses = useMemo(() => {
    if (filterCategory === 'ALL') return expenses;
    return expenses.filter((e) => e.category === filterCategory);
  }, [expenses, filterCategory]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600">
              <Wallet className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Site Petty Cash & Out-of-Pocket Wallet</h1>
              <p className="text-xs sm:text-sm text-gray-500">Live Balance, Permissive Deficit Monitoring & Tally Exports</p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleTallyExport}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3.5 py-2 text-xs font-semibold text-gray-700 shadow-sm hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <Download className="h-3.5 w-3.5 text-gray-500" />
            Export Tally XML
          </button>

          <button
            type="button"
            onClick={() => setIsReimburseModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3.5 py-2 text-xs font-semibold text-indigo-700 shadow-sm hover:bg-indigo-100 transition-colors cursor-pointer"
          >
            <Receipt className="h-3.5 w-3.5 text-indigo-600" />
            Claim Reimbursement
          </button>

          <button
            type="button"
            onClick={() => setIsExpenseModalOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500 transition-colors cursor-pointer"
          >
            <PlusCircle className="h-3.5 w-3.5" />
            Log New Expense
          </button>
        </div>
      </div>

      {/* Notifications */}
      {toastMessage && (
        <div
          className={`rounded-lg p-4 border flex items-start gap-3 shadow-sm ${
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
          <button
            onClick={() => setToastMessage(null)}
            className="text-xs font-semibold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Wallet Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Balance Card */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Site Wallet Balance</span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={fetchWallet}
                disabled={isLoadingWallet}
                title="Refresh wallet balance"
                className="p-1 rounded-md text-emerald-600 hover:bg-emerald-50"
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
          <p className="mt-1 text-[11px] text-gray-500">Available cash for emergency purchases & food</p>
        </div>

        {/* Deficit Card */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Out-of-Pocket Deficit</span>
            <span className="p-1.5 bg-amber-50 text-amber-600 rounded-md">
              <TrendingDown className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-amber-600">
            ₹{supervisorDeficit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="mt-1 flex items-center gap-1.5 text-[11px] text-gray-500">
            <span>Spent from supervisor funds</span>
            <span className="text-amber-700 font-medium">• Reimbursement Due</span>
          </div>
        </div>

        {/* Deficit Cap Limit Card */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">₹50,000 Deficit Cap</span>
            <span className={`p-1.5 rounded-md ${supervisorDeficit > 40000 ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>
              <AlertTriangle className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-gray-900">
            ₹{Math.max(0, 50000 - supervisorDeficit).toLocaleString('en-IN')}
          </div>
          <div className="mt-2 w-full bg-gray-100 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${
                supervisorDeficit > 40000 ? 'bg-red-500' : 'bg-indigo-500'
              }`}
              style={{ width: `${Math.min(100, (supervisorDeficit / 50000) * 100)}%` }}
            />
          </div>
          <p className="mt-1 text-[11px] text-gray-400">Enforced by AnomalyDetector guard</p>
        </div>
      </div>

      {/* Critical Deficit Alert Banner if > 40,000 */}
      {supervisorDeficit > 40000 && (
        <div className="rounded-xl bg-red-50 p-4 border border-red-200 flex items-start gap-3 shadow-sm">
          <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-bold text-red-900">Critical Deficit Warning</h3>
            <p className="text-xs text-red-700 mt-0.5">
              Current out-of-pocket deficit (₹{supervisorDeficit.toLocaleString()}) is approaching the strict ₹50,000 cap.
              Any expense pushing cumulative deficit past ₹50,000 will be blocked to prevent unapproved field liabilities.
            </p>
          </div>
        </div>
      )}

      {/* Transactions Section */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-gray-900">Recent Site Expenses & Vouchers</h2>
            <p className="text-xs text-gray-500">Track receipts, duplicate warnings, and reimbursement status</p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Category:</span>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="rounded-lg border border-gray-300 px-2.5 py-1 text-xs shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
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
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-100 text-gray-800">
                      {tx.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-800 max-w-xs truncate">
                    <div className="font-medium text-gray-900">{tx.description}</div>
                    {tx.has_physical_bill && (
                      <span className="text-[10px] text-emerald-600 font-medium flex items-center gap-1 mt-0.5">
                        <Receipt className="h-3 w-3" /> Bill Attached
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-bold text-gray-900 whitespace-nowrap">
                    ₹{tx.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-3 text-center whitespace-nowrap">
                    {tx.is_out_of_pocket ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                        Out-of-Pocket
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Wallet Direct
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center whitespace-nowrap">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        tx.approval_status === 'APPROVED'
                          ? 'bg-green-100 text-green-800'
                          : tx.approval_status === 'REJECTED'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {tx.approval_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center whitespace-nowrap">
                    {tx.reimbursement_status === 'DUE' ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200">
                        Claim Due
                      </span>
                    ) : tx.reimbursement_status === 'SETTLED' ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                        Settled
                      </span>
                    ) : (
                      <span className="text-gray-400 text-[10px]">N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log Expense Modal */}
      {isExpenseModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-gray-900/60 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-xl border border-gray-100 overflow-hidden animate-scale-in">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-2">
                <PlusCircle className="h-5 w-5 text-emerald-600" />
                <h3 className="text-base font-bold text-gray-900">Log Site Expense</h3>
              </div>
              <button
                onClick={() => setIsExpenseModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded-lg"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleExpenseSubmit} className="p-6 space-y-4">
              {/* Duplicate Warning Feedback */}
              {duplicateWarning && (
                <div className="rounded-lg bg-amber-50 p-3 border border-amber-200 flex items-start gap-2 text-xs text-amber-800">
                  <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div>{duplicateWarning}</div>
                </div>
              )}

              {/* Deficit Cap Warning Feedback */}
              {deficitCapWarning && (
                <div
                  className={`rounded-lg p-3 border flex items-start gap-2 text-xs ${
                    deficitCapWarning.isExceeded
                      ? 'bg-red-50 border-red-200 text-red-800 font-semibold'
                      : 'bg-amber-50 border-amber-200 text-amber-800'
                  }`}
                >
                  <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
                  <div>{deficitCapWarning.message}</div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700">Amount (₹) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="e.g. 2500"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 font-bold"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700">Category *</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                  >
                    <option value="DIESEL">Diesel</option>
                    <option value="SPARES">Spares & Seals</option>
                    <option value="FOOD_WATER">Food & Drinking Water</option>
                    <option value="TRANSPORT">Transport / Freight</option>
                    <option value="LABOUR">Unloading / Direct Labour</option>
                    <option value="TOOLS">Tools & Small Equipment</option>
                    <option value="WELDING_REPAIR">Welding & Machine Repair</option>
                    <option value="OTHER">Other Contingency</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Description / Vendor *</label>
                <input
                  type="text"
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Diesel for standby generator pump - Bharat Petroleum"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700">Date *</label>
                  <input
                    type="date"
                    required
                    value={expenseDate}
                    onChange={(e) => setExpenseDate(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-xs shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700">Quantity</label>
                  <input
                    type="number"
                    step="0.1"
                    value={quantity}
                    onChange={(e) => setQuantity(e.target.value)}
                    placeholder="e.g. 25"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-xs shadow-sm"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700">Unit</label>
                  <input
                    type="text"
                    value={unit}
                    onChange={(e) => setUnit(e.target.value)}
                    placeholder="Liters/Bags"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-xs shadow-sm"
                  />
                </div>
              </div>

              {/* Out-of-pocket & Bill Toggles */}
              <div className="space-y-2 border-t border-gray-100 pt-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isOutOfPocket}
                    onChange={(e) => setIsOutOfPocket(e.target.checked)}
                    className="rounded border-gray-300 text-amber-600 focus:ring-amber-500 h-4 w-4"
                  />
                  <span className="text-xs font-medium text-gray-800">
                    Paid Out-of-Pocket by Supervisor (Claim Reimbursement)
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={hasPhysicalBill}
                    onChange={(e) => setHasPhysicalBill(e.target.checked)}
                    className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500 h-4 w-4"
                  />
                  <span className="text-xs font-medium text-gray-800">
                    Physical Bill / Cash Memo Available
                  </span>
                </label>
              </div>

              {/* Receipt Photo Upload with Canvas Compression */}
              <div className="border-t border-gray-100 pt-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                    <Camera className="h-4 w-4 text-emerald-600" />
                    Receipt Photo (Canvas Compression)
                  </label>
                  <label className="cursor-pointer px-2.5 py-1 text-xs font-medium rounded-md bg-emerald-50 text-emerald-700 hover:bg-emerald-100">
                    <span>Upload Bill</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handlePhotoUpload}
                      className="hidden"
                    />
                  </label>
                </div>

                {isCompressing && (
                  <p className="text-[11px] text-emerald-600 animate-pulse mt-1">Compressing bill image...</p>
                )}

                {receiptPhoto && (
                  <div className="mt-2 flex items-center gap-3 p-2 rounded-lg border border-gray-200 bg-gray-50">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={receiptPhoto.dataUrl} alt="Bill preview" className="h-12 w-12 rounded object-cover" />
                    <div className="flex-1 text-[11px] truncate">
                      <div className="font-semibold text-gray-900 truncate">{receiptPhoto.name}</div>
                      <div className="text-gray-500">{formatFileSize(receiptPhoto.compressedSize)}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setReceiptPhoto(null)}
                      className="text-red-500 hover:text-red-700 p-1"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>

              {/* Form Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsExpenseModalOpen(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || Boolean(deficitCapWarning?.isExceeded)}
                  className="rounded-lg bg-emerald-600 px-5 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:opacity-50 transition-colors cursor-pointer"
                >
                  {isSubmitting ? 'Recording...' : 'Record Expense'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reimbursement Modal */}
      {isReimburseModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-gray-900/60 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-md rounded-2xl shadow-xl border border-gray-100 overflow-hidden animate-scale-in">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-2">
                <Receipt className="h-5 w-5 text-indigo-600" />
                <h3 className="text-base font-bold text-gray-900">Claim Reimbursement</h3>
              </div>
              <button
                onClick={() => setIsReimburseModalOpen(false)}
                className="p-1 text-gray-400 hover:text-gray-600 rounded-lg"
              >
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
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-bold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Reimbursement Reference No.</label>
                <input
                  type="text"
                  value={reimburseRef}
                  onChange={(e) => setReimburseRef(e.target.value)}
                  placeholder="e.g. CLAIM-SEPT-WEEK3"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setIsReimburseModalOpen(false)}
                  className="rounded-lg px-4 py-2 text-xs font-medium text-gray-700 hover:bg-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="rounded-lg bg-indigo-600 px-5 py-2.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500 transition-colors cursor-pointer"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Claim'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
