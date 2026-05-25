import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { useThemeStore } from '../store/themeStore'
import { useNavigate } from 'react-router-dom'
import { 
  User, Shield, Landmark, Settings2, 
  LogOut, CheckCircle2, AlertCircle, Smartphone, Monitor, ShieldCheck, Mail, ArrowRight, ChevronRight, Plus, Sun, Moon
} from 'lucide-react'

function TabButton({ active, icon: Icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200
        ${active 
          ? 'bg-slate-100 dark:bg-arcx-gold/10 text-[#1D1D1F] dark:text-arcx-gold shadow-sm dark:shadow-none' 
          : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-black/5 dark:hover:bg-white/5'
        }`}
    >
      <Icon size={16} />
      {label}
    </button>
  )
}

function SectionCard({ title, children }) {
  return (
    <div className="bg-white dark:bg-[#1C1C1E] border border-black/5 dark:border-white/5 rounded-2xl p-6 mb-6 shadow-sm dark:shadow-none transition-colors duration-300">
      {title && <h2 className="text-sm font-bold text-slate-500 dark:text-slate-300 uppercase tracking-widest mb-6 transition-colors">{title}</h2>}
      {children}
    </div>
  )
}

function ProfileTab({ user, navigate }) {
  const isVerified = user?.kyc_status === 'approved'

  return (
    <div className="animate-fade-in transition-colors duration-300">
      <SectionCard title="Personal Information">
        <div className="flex items-center gap-6 mb-8">
          <div className="w-20 h-20 rounded-full bg-slate-100 dark:bg-arcx-gold/10 border border-black/5 dark:border-arcx-gold/20 flex items-center justify-center text-3xl font-display font-bold text-[#C5A059] dark:text-arcx-gold transition-colors">
            {user?.full_name ? user.full_name[0].toUpperCase() : 'U'}
          </div>
          <div>
            <h3 className="text-xl font-display font-bold text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">{user?.full_name || 'ARCX User'}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 transition-colors">{user?.email}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider mb-1 block transition-colors">Full Name</label>
            <div className="text-sm text-[#1D1D1F] dark:text-[#F5F5F7] bg-slate-50 dark:bg-black/50 border border-black/5 dark:border-white/5 rounded-lg px-4 py-2.5 transition-colors">
              {user?.full_name || '—'}
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider mb-1 block transition-colors">Phone Number</label>
            <div className="text-sm text-[#1D1D1F] dark:text-[#F5F5F7] bg-slate-50 dark:bg-black/50 border border-black/5 dark:border-white/5 rounded-lg px-4 py-2.5 transition-colors">
              {user?.phone || 'Not Provided'}
            </div>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Identity Verification">
        <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-black/50 border border-black/5 dark:border-white/5 rounded-xl transition-colors">
          <div className="flex items-center gap-4">
            {isVerified ? (
              <div className="w-10 h-10 rounded-full bg-emerald-100 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400 transition-colors">
                <ShieldCheck size={20} />
              </div>
            ) : (
              <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-500/10 flex items-center justify-center text-amber-600 dark:text-amber-400 transition-colors">
                <AlertCircle size={20} />
              </div>
            )}
            <div>
              <div className="text-sm font-bold text-[#1D1D1F] dark:text-[#F5F5F7] flex items-center gap-2 transition-colors">
                KYC Status
                <span className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider font-bold transition-colors ${isVerified ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400' : 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400'}`}>
                  {isVerified ? 'Verified' : 'Pending'}
                </span>
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 transition-colors">Tier {user?.kyc_tier || 1} — Daily Limit: {isVerified ? 'Unlimited' : '₹0'}</div>
            </div>
          </div>
          <button 
            onClick={() => navigate('/kyc')}
            className="flex items-center gap-1 text-sm font-medium text-[#C5A059] dark:text-arcx-gold hover:text-[#B38F48] dark:hover:text-arcx-gold/80 transition-colors"
          >
            Manage KYC <ArrowRight size={16} />
          </button>
        </div>
      </SectionCard>
    </div>
  )
}

function SecurityTab() {
  return (
    <div className="animate-fade-in transition-colors duration-300">
      <SectionCard title="Authentication">
        <div className="flex items-center justify-between py-4 border-b border-black/5 dark:border-white/5 transition-colors">
          <div>
            <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Password</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 transition-colors">Last changed 3 months ago</div>
          </div>
          <button className="px-4 py-2 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 border border-black/5 dark:border-white/10 rounded-lg text-sm text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">
            Update
          </button>
        </div>
        <div className="flex items-center justify-between py-4">
          <div>
            <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] flex items-center gap-2 transition-colors">
              Two-Factor Authentication (2FA)
              <span className="px-1.5 py-0.5 bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400 text-[10px] uppercase font-bold rounded transition-colors">Off</span>
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 transition-colors">Protect your account with an authenticator app.</div>
          </div>
          <button className="px-4 py-2 bg-[#1D1D1F] dark:bg-arcx-gold text-white dark:text-black hover:bg-black dark:hover:bg-[#E5C009] font-medium rounded-lg text-sm transition-colors">
            Enable 2FA
          </button>
        </div>
      </SectionCard>

      <SectionCard title="Active Sessions">
        <div className="space-y-4">
          <div className="flex items-start gap-4 p-4 bg-slate-50 dark:bg-black/50 border border-black/5 dark:border-white/5 rounded-xl transition-colors">
            <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-white/5 flex items-center justify-center text-slate-500 dark:text-slate-300 flex-shrink-0 transition-colors">
              <Monitor size={18} />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] flex items-center gap-2 transition-colors">
                Windows PC — Chrome
                <span className="px-1.5 py-0.5 bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-[10px] uppercase font-bold rounded transition-colors">Current Session</span>
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 transition-colors">Mumbai, India • Last active: Just now</div>
            </div>
          </div>
          <div className="flex items-start gap-4 p-4 bg-slate-50 dark:bg-black/50 border border-black/5 dark:border-white/5 rounded-xl transition-colors">
            <div className="w-10 h-10 rounded-full bg-slate-200 dark:bg-white/5 flex items-center justify-center text-slate-500 dark:text-slate-300 flex-shrink-0 transition-colors">
              <Smartphone size={18} />
            </div>
            <div className="flex-1">
              <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">
                iPhone 14 Pro — Safari
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 transition-colors">Delhi, India • Last active: 2 days ago</div>
            </div>
            <button className="text-xs font-medium text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 transition-colors">
              Revoke
            </button>
          </div>
        </div>
      </SectionCard>
    </div>
  )
}

function BankAccountsTab({ user }) {
  const isVerified = user?.kyc_status === 'approved'

  return (
    <div className="animate-fade-in transition-colors duration-300">
      <SectionCard title="Account Limits">
        <div className="mb-2 flex justify-between items-end">
          <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Daily Withdrawal Limit</div>
          <div className="text-xs text-slate-500 dark:text-slate-400 transition-colors">
            <span className="text-[#1D1D1F] dark:text-[#F5F5F7] font-medium transition-colors">₹0</span> / {isVerified ? '₹1,00,000' : '₹0'}
          </div>
        </div>
        <div className="h-2 w-full bg-slate-200 dark:bg-black/50 rounded-full overflow-hidden border border-black/5 dark:border-white/5 transition-colors">
          <div className="h-full bg-[#1D1D1F] dark:bg-arcx-gold w-[5%] rounded-full transition-colors" />
        </div>
        <p className="text-[11px] text-slate-500 mt-2 transition-colors">
          {isVerified ? 'Limits reset daily at midnight UTC.' : 'Complete KYC to unlock withdrawals.'}
        </p>
      </SectionCard>

      <SectionCard title="Linked Banks">
        <div className="flex flex-col items-center justify-center py-8 px-4 text-center border border-dashed border-black/10 dark:border-white/10 rounded-xl bg-slate-50 dark:bg-black/20 transition-colors">
          <Landmark size={32} className="text-slate-400 dark:text-slate-600 mb-3 transition-colors" />
          <div className="text-sm font-medium text-[#1D1D1F] dark:text-slate-300 mb-1 transition-colors">No bank accounts linked</div>
          <div className="text-xs text-slate-500 dark:text-slate-500 mb-4 max-w-xs transition-colors">
            Link a bank account to deposit INR and withdraw your ARCX balance.
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-slate-200 dark:bg-white/5 hover:bg-slate-300 dark:hover:bg-white/10 border border-black/5 dark:border-white/10 rounded-lg text-sm text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">
            <Plus size={16} />
            Add Bank Account
          </button>
        </div>
      </SectionCard>
    </div>
  )
}

function PreferencesTab() {
  const { theme, setTheme } = useThemeStore()

  return (
    <div className="animate-fade-in transition-colors duration-300">
      
      {/* Theme Toggle */}
      <SectionCard title="Appearance">
        <div className="flex items-center justify-between py-4">
          <div>
            <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">App Theme</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 transition-colors">Select your preferred viewing experience.</div>
          </div>
          <div className="flex bg-slate-100 dark:bg-black/50 p-1 rounded-xl border border-black/5 dark:border-white/5 transition-colors">
            <button 
              onClick={() => setTheme('light')}
              className={`flex items-center justify-center w-10 h-8 rounded-lg transition-all duration-300 ${theme === 'light' ? 'bg-white text-[#1D1D1F] shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
              title="Light Mode"
            >
              <Sun size={14} strokeWidth={2.5} />
            </button>
            <button 
              onClick={() => setTheme('dark')}
              className={`flex items-center justify-center w-10 h-8 rounded-lg transition-all duration-300 ${theme === 'dark' ? 'bg-white/10 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
              title="Dark Mode"
            >
              <Moon size={14} strokeWidth={2.5} />
            </button>
            <button 
              onClick={() => setTheme('system')}
              className={`flex items-center justify-center w-10 h-8 rounded-lg transition-all duration-300 ${theme === 'system' ? 'bg-white dark:bg-white/10 text-[#1D1D1F] dark:text-[#F5F5F7] shadow-sm' : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'}`}
              title="System Default"
            >
              <Monitor size={14} strokeWidth={2.5} />
            </button>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="Localization">
        <div className="flex items-center justify-between py-4 border-b border-black/5 dark:border-white/5 transition-colors">
          <div>
            <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Display Currency</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 transition-colors">Your portfolio will be displayed in this currency.</div>
          </div>
          <select className="bg-slate-50 dark:bg-black/50 border border-black/10 dark:border-white/10 rounded-lg px-3 py-1.5 text-sm text-[#1D1D1F] dark:text-[#F5F5F7] outline-none focus:border-[#C5A059] dark:focus:border-arcx-gold transition-colors">
            <option value="INR">INR (₹)</option>
            <option value="USD">USD ($)</option>
          </select>
        </div>
      </SectionCard>

      <SectionCard title="Email Notifications">
        <div className="flex items-center justify-between py-4 border-b border-black/5 dark:border-white/5 transition-colors">
          <div>
            <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Account Alerts (Required)</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 transition-colors">Security alerts, login attempts, and password resets.</div>
          </div>
          <div className="w-10 h-6 bg-emerald-200 dark:bg-emerald-500/20 rounded-full p-1 cursor-not-allowed transition-colors">
            <div className="w-4 h-4 bg-emerald-600 dark:bg-emerald-500 rounded-full translate-x-4 transition-colors" />
          </div>
        </div>
        <div className="flex items-center justify-between py-4 border-b border-black/5 dark:border-white/5 transition-colors">
          <div>
            <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Transaction Updates</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 transition-colors">Receipts for deposits, withdrawals, and transfers.</div>
          </div>
          <div className="w-10 h-6 bg-emerald-200 dark:bg-emerald-500/20 rounded-full p-1 cursor-pointer transition-colors">
            <div className="w-4 h-4 bg-emerald-600 dark:bg-emerald-500 rounded-full translate-x-4 transition-colors" />
          </div>
        </div>
        <div className="flex items-center justify-between py-4">
          <div>
            <div className="text-sm font-medium text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Product & Marketing</div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 transition-colors">Newsletter, feature updates, and promotions.</div>
          </div>
          <div className="w-10 h-6 bg-slate-200 dark:bg-white/10 rounded-full p-1 cursor-pointer transition-colors">
            <div className="w-4 h-4 bg-white dark:bg-white/40 rounded-full transition-colors" />
          </div>
        </div>
      </SectionCard>
    </div>
  )
}

export default function ProfilePage() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('profile')

  const handleLogout = async () => {
    if (window.confirm('Are you sure you want to sign out?')) {
      await logout()
      navigate('/auth')
    }
  }

  return (
    <div className="max-w-[800px] mx-auto pb-20 transition-colors duration-300">
      
      {/* Header */}
      <div className="flex items-center justify-between mb-8 mt-2">
        <div>
          <h1 className="font-display font-bold text-[28px] text-[#1D1D1F] dark:text-[#F5F5F7] transition-colors">Settings</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 transition-colors">Manage your account, security, and preferences.</p>
        </div>
        <button 
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 bg-red-100 dark:bg-red-500/10 hover:bg-red-200 dark:hover:bg-red-500/20 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-500/20 rounded-xl text-sm font-medium transition-colors"
        >
          <LogOut size={16} /> Sign Out
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-8 border-b border-black/5 dark:border-white/5 pb-4 overflow-x-auto no-scrollbar transition-colors">
        <TabButton active={activeTab === 'profile'} icon={User} label="Profile" onClick={() => setActiveTab('profile')} />
        <TabButton active={activeTab === 'security'} icon={Shield} label="Security" onClick={() => setActiveTab('security')} />
        <TabButton active={activeTab === 'banks'} icon={Landmark} label="Bank Accounts" onClick={() => setActiveTab('banks')} />
        <TabButton active={activeTab === 'preferences'} icon={Settings2} label="Preferences" onClick={() => setActiveTab('preferences')} />
      </div>

      {/* Content */}
      <div className="min-h-[400px]">
        {activeTab === 'profile' && <ProfileTab user={user} navigate={navigate} />}
        {activeTab === 'security' && <SecurityTab />}
        {activeTab === 'banks' && <BankAccountsTab user={user} />}
        {activeTab === 'preferences' && <PreferencesTab />}
      </div>

    </div>
  )
}
