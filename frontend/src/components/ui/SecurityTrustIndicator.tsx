'use client';

import React, { useState } from 'react';
import { Activity } from 'lucide-react';
import Modal from './Modal';

export interface SecurityTrustIndicatorProps {
  userRole?: string;
  userName?: string;
}

export const SecurityTrustIndicator: React.FC<SecurityTrustIndicatorProps> = ({
  userRole = 'Authorized User',
  userName = 'Operator',
}) => {
  const [isAuditOpen, setIsAuditOpen] = useState(false);

  // Discreet mock audit trail for confidentiality compliance (Section 6)
  const auditEntries = [
    { action: 'Session Initialized', actor: userName, time: '08:00 AM', detail: 'Encrypted token validated via HMAC SHA-256' },
    { action: 'DPR P-104 Inspected', actor: 'Vikram Mehta (PM)', time: '08:42 AM', detail: 'Viewed boring log & concrete overbreak' },
    { action: 'Petty Cash Voucher #2 Created', actor: 'Rajesh Sharma', time: '09:15 AM', detail: 'Bauer rig replacement hydraulic seal' },
    { action: 'AI Verification Analysis', actor: 'Autonomous System', time: '09:30 AM', detail: 'Anomaly engine completed 3-channel evaluation' },
  ];

  return (
    <>
      <button
        type="button"
        onClick={() => setIsAuditOpen(true)}
        title="Encrypted Session & Audit Trail"
        className="inline-flex items-center gap-2 px-2.5 py-1 rounded-pill bg-surface-sunk/80 border border-border hover:border-border-strong text-text-muted hover:text-text text-xs transition-colors duration-fast select-none cursor-pointer"
      >
        <span className="flex h-2 w-2 rounded-pill bg-status-success" />
        <span className="font-mono text-[11px] uppercase tracking-wider font-semibold text-text">
          Secure
        </span>
        <span className="hidden lg:inline text-text-faint">•</span>
        <span className="hidden lg:inline text-text-faint text-[11px] truncate max-w-[120px]">
          {userRole.replace('_', ' ')}
        </span>
      </button>

      {/* Discreet Activity / Audit Trail Modal (Section 6) */}
      <Modal
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
        title="Audit Trail & Security Verification"
        description="Immutable record of system access, state inspections, and cryptographic session parameters."
        maxWidth="lg"
      >
        <div className="space-y-4">
          <div className="p-3 bg-surface-sunk rounded-md border border-border flex items-center justify-between text-xs">
            <div>
              <div className="font-semibold text-text">TLS 1.3 / End-to-End Integrity</div>
              <div className="text-text-faint text-[11px]">Strict Role-Based Access Control • Active Site #1</div>
            </div>
            <span className="px-2 py-0.5 rounded-pill bg-status-success-soft text-status-success font-medium text-[10px] border border-status-success/20">
              Verified Active
            </span>
          </div>

          <div className="pt-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-3 flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5" />
              <span>Recent Activity Trail</span>
            </h4>

            <div className="space-y-2.5 border-l-2 border-border ml-2 pl-4">
              {auditEntries.map((entry, idx) => (
                <div key={idx} className="relative text-xs">
                  <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-pill bg-accent-soft border border-accent" />
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-text">{entry.action}</span>
                    <span className="text-[10px] text-text-faint font-mono">{entry.time}</span>
                  </div>
                  <div className="text-text-muted text-[11px] mt-0.5">{entry.detail}</div>
                  <div className="text-[10px] text-text-faint mt-0.5">By {entry.actor}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Modal>
    </>
  );
};

export default SecurityTrustIndicator;
