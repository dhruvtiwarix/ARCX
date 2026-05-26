import { useState, useEffect } from 'react';
import { adminApi } from '../api';
import { 
  Users, ShieldAlert, Activity, CheckCircle2, XCircle, 
  Loader2, Calculator, ShieldCheck
} from 'lucide-react';

function Flash({ type, msg }) {
  if (!msg) return null;
  return (
    <div className={`flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium mb-6 animate-fade-in transition-colors
      ${type === 'ok'
        ? 'bg-emerald-100 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-400'
        : 'bg-red-100 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-700 dark:text-red-400'}`}>
      {type === 'ok' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
      {msg}
    </div>
  );
}

function AdminTabs({ active, onSelect }) {
  const tabs = [
    { id: 'users', label: 'Users', icon: Users },
    { id: 'kyc', label: 'KYC Reviews', icon: ShieldCheck },
    { id: 'system', label: 'System Ops', icon: Activity },
  ];
  return (
    <div className="flex bg-slate-100 dark:bg-black/50 p-1 rounded-xl border border-black/5 dark:border-white/5 mb-6 transition-colors max-w-fit">
      {tabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onSelect(id)}
          className={`flex items-center gap-2 px-6 py-2.5 text-xs font-bold uppercase tracking-widest rounded-lg transition-all duration-300
            ${active === id
              ? 'bg-white dark:bg-white/10 text-[#1D1D1F] dark:text-[#F5F5F7] shadow-sm'
              : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'}`}
        >
          <Icon size={16} /> {label}
        </button>
      ))}
    </div>
  );
}

export default function AdminPage() {
  const [tab, setTab] = useState('users');
  const [loading, setLoading] = useState(false);
  const [flash, setFlash] = useState(null);
  
  const [users, setUsers] = useState([]);
  const [kycRecords, setKycRecords] = useState([]);

  const showFlash = (type, msg) => {
    setFlash({ type, msg });
    setTimeout(() => setFlash(null), 5000);
  };

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getUsers();
      setUsers(data.users || []);
    } catch (e) {
      showFlash('err', 'Failed to load users');
    }
    setLoading(false);
  };

  const loadKYC = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getPendingKYC();
      setKycRecords(data.pending_kyc || []);
    } catch (e) {
      showFlash('err', 'Failed to load KYC records');
    }
    setLoading(false);
  };

  useEffect(() => {
    if (tab === 'users') loadUsers();
    else if (tab === 'kyc') loadKYC();
  }, [tab]);

  const handleKYCAction = async (recordId, action) => {
    try {
      await adminApi.updateKYCStatus(recordId, action);
      showFlash('ok', `KYC Record ${action}d successfully`);
      loadKYC(); // reload
    } catch (e) {
      showFlash('err', `Failed to ${action} KYC: ${e.response?.data?.error || e.message}`);
    }
  };

  const handleComputeNAV = async () => {
    setLoading(true);
    try {
      const data = await adminApi.computeNAV();
      showFlash('ok', `NAV Computed! ₹${data.nav_inr} | $${data.nav_usd} for ${data.date}`);
    } catch (e) {
      showFlash('err', `NAV Computation Failed: ${e.response?.data?.error || e.message}`);
    }
    setLoading(false);
  };

  return (
    <div className="animate-fade-in pb-12 transition-colors duration-300">
      <div className="mb-10">
        <h1 className="font-display font-bold text-[28px] text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors flex items-center gap-3">
          <ShieldAlert className="text-red-600 dark:text-red-400" />
          Treasury Ops
        </h1>
        <p className="text-sm text-slate-500 mt-1 transition-colors">
          Superuser portal for ARCX management.
        </p>
      </div>

      <AdminTabs active={tab} onSelect={setTab} />
      {flash && <Flash type={flash.type} msg={flash.msg} />}

      {/* ── Users Tab ──────────────────────────────────────────────────────── */}
      {tab === 'users' && (
        <div className="bg-white dark:glass-container border border-black/5 dark:border-0 rounded-[24px] overflow-hidden shadow-sm dark:shadow-none transition-colors duration-300">
          <div className="p-6 border-b border-black/5 dark:border-white/10 bg-slate-50 dark:bg-black/20 flex items-center justify-between">
            <h3 className="font-display font-bold text-lg text-[#1D1D1F] dark:text-[#F5F5F7]">Platform Users</h3>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">{users.length} Total</span>
          </div>
          
          {loading ? (
             <div className="p-12 flex justify-center"><Loader2 className="animate-spin text-slate-400" /></div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 dark:bg-white/5 text-slate-500 text-xs uppercase tracking-wider font-bold">
                  <tr>
                    <th className="px-6 py-4">User</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">ARCX Balance</th>
                    <th className="px-6 py-4 text-right">Cost Basis (INR)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/5 dark:divide-white/5 text-[#1D1D1F] dark:text-[#F5F5F7]">
                  {users.map(u => (
                    <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-bold">{u.full_name}</div>
                        <div className="text-xs text-slate-500">{u.email}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 rounded text-[10px] uppercase font-bold tracking-wider ${
                          u.kyc_status === 'approved' ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' :
                          u.kyc_status === 'pending' ? 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400' :
                          'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400'
                        }`}>
                          {u.kyc_status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-mono font-bold text-arcx-gold">{u.arcx_balance.toFixed(4)}</td>
                      <td className="px-6 py-4 text-right">₹{u.cost_basis_inr.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── KYC Tab ────────────────────────────────────────────────────────── */}
      {tab === 'kyc' && (
        <div className="bg-white dark:glass-container border border-black/5 dark:border-0 rounded-[24px] p-6 shadow-sm dark:shadow-none transition-colors duration-300">
          <h3 className="font-display font-bold text-lg text-[#1D1D1F] dark:text-[#F5F5F7] mb-6">Pending KYC Approvals</h3>
          
          {loading ? (
            <div className="p-12 flex justify-center"><Loader2 className="animate-spin text-slate-400" /></div>
          ) : kycRecords.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-sm">No pending KYC records. Queue is clear!</div>
          ) : (
            <div className="space-y-4">
              {kycRecords.map(r => (
                <div key={r.id} className="p-5 rounded-xl border border-black/5 dark:border-white/10 bg-slate-50 dark:bg-black/20 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-[#1D1D1F] dark:text-[#F5F5F7]">{r.user_email}</div>
                    <div className="text-xs text-slate-500 mt-1 flex gap-3">
                      <span className="uppercase font-bold tracking-wider">{r.tier.replace('_', ' ')}</span>
                      <span>Doc: {r.document_type.toUpperCase()}</span>
                      <span className="font-mono bg-slate-200 dark:bg-white/10 px-1 rounded">{r.document_ref}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => handleKYCAction(r.id, 'approve')}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold uppercase tracking-wider rounded-lg transition-colors"
                    >
                      Approve
                    </button>
                    <button 
                      onClick={() => handleKYCAction(r.id, 'reject')}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold uppercase tracking-wider rounded-lg transition-colors"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── System Tab ─────────────────────────────────────────────────────── */}
      {tab === 'system' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:glass-container border border-black/5 dark:border-0 rounded-[24px] p-6 shadow-sm dark:shadow-none transition-colors duration-300">
            <div className="w-12 h-12 bg-indigo-100 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded-full flex items-center justify-center mb-4">
              <Calculator size={24} />
            </div>
            <h3 className="font-display font-bold text-lg text-[#1D1D1F] dark:text-[#F5F5F7] mb-2">On-Demand NAV Compute</h3>
            <p className="text-sm text-slate-500 mb-6">
              Manually trigger the End-of-Day Valuation Engine. This fetches live prices from multiple oracles and calculates the exact NAV per ARCX token.
            </p>
            <button 
              onClick={handleComputeNAV}
              disabled={loading}
              className="w-full py-3.5 bg-[#1D1D1F] dark:bg-white text-white dark:text-black font-bold rounded-xl hover:bg-black dark:hover:bg-slate-200 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="animate-spin" /> : 'Run NAV Engine'}
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
