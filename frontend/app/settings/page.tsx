'use client';

import React, { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import {
  Shield,
  KeyRound,
  Bell,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Eye,
  EyeOff,
  Save,
  Lock,
  User as UserIcon,
  Calendar,
  Check,
  Info,
} from 'lucide-react';
import { userAPI, User, NotificationSettings } from '@/lib/api';

export default function SettingsPage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);

  // Password Change State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);

  // Notification Preferences State
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings>({
    exam_reminders: true,
    result_notifications: true,
    integrity_alerts: true,
    system_updates: true,
  });
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [settingsSuccess, setSettingsSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoadingUser(true);
      setSettingsLoading(true);
      try {
        const [user, settings] = await Promise.all([
          userAPI.getProfile(),
          userAPI.getSettings().catch(() => ({
            exam_reminders: true,
            result_notifications: true,
            integrity_alerts: true,
            system_updates: true,
          })),
        ]);
        setCurrentUser(user);
        setNotificationSettings(settings);
      } catch (err: any) {
        console.error('Failed to load settings data:', err);
      } finally {
        setLoadingUser(false);
        setSettingsLoading(false);
      }
    }
    loadData();
  }, []);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (!currentPassword) {
      setPasswordError('Current password is required.');
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    setPasswordLoading(true);
    try {
      await userAPI.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordSuccess('Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => {
        setPasswordSuccess(null);
      }, 4000);
    } catch (err: any) {
      setPasswordError(err?.message || 'Failed to update password.');
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleTogglePreference = (key: keyof NotificationSettings) => {
    setNotificationSettings((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
    setSettingsSuccess(null);
  };

  const handleSaveNotifications = async () => {
    setSettingsSaving(true);
    setSettingsError(null);
    setSettingsSuccess(null);
    try {
      const updated = await userAPI.updateSettings(notificationSettings);
      setNotificationSettings(updated);
      setSettingsSuccess('Notification preferences saved successfully.');
      setTimeout(() => {
        setSettingsSuccess(null);
      }, 4000);
    } catch (err: any) {
      setSettingsError(err?.message || 'Failed to save notification preferences.');
    } finally {
      setSettingsSaving(false);
    }
  };

  return (
    <AppShell title="Account Settings">
      <div className="max-w-4xl mx-auto space-y-8 pb-16">
        <PageHeader
          title="Account Settings"
          subtitle="Manage your security credentials, notification preferences, and account configuration."
        />

        {/* SECTION 1: ACCOUNT SECURITY & PASSWORD CHANGE */}
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-6 shadow-xl">
          <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <KeyRound className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">Account Security</h3>
              <p className="text-xs text-slate-400">
                Update your account password to maintain system security.
              </p>
            </div>
          </div>

          {passwordError && (
            <div className="p-3.5 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{passwordError}</span>
            </div>
          )}

          {passwordSuccess && (
            <div className="p-3.5 bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs rounded-xl flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{passwordSuccess}</span>
            </div>
          )}

          <form onSubmit={handlePasswordSubmit} className="space-y-4 max-w-lg">
            {/* Current Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Current Password <span className="text-rose-400">*</span>
              </label>
              <div className="relative">
                <input
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  placeholder="Enter current password"
                  className="w-full pl-3.5 pr-10 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-indigo-500 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* New Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                New Password <span className="text-rose-400">*</span>
              </label>
              <div className="relative">
                <input
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={8}
                  placeholder="At least 8 characters"
                  className="w-full pl-3.5 pr-10 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-indigo-500 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-[11px] text-slate-500">
                Must be at least 8 characters long.
              </p>
            </div>

            {/* Confirm New Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Confirm New Password <span className="text-rose-400">*</span>
              </label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={8}
                  placeholder="Re-enter new password"
                  className="w-full pl-3.5 pr-10 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-indigo-500 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={passwordLoading || !currentPassword || !newPassword || !confirmPassword}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2 disabled:opacity-50"
              >
                {passwordLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Updating Password...
                  </>
                ) : (
                  <>
                    <Lock className="w-4 h-4" /> Update Password
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* SECTION 2: NOTIFICATION PREFERENCES */}
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-6 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                <Bell className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">Notification Preferences</h3>
                <p className="text-xs text-slate-400">
                  Configure alerts and platform communication preferences.
                </p>
              </div>
            </div>

            <button
              onClick={handleSaveNotifications}
              disabled={settingsSaving}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2 disabled:opacity-50"
            >
              {settingsSaving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Saving...
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" /> Save Preferences
                </>
              )}
            </button>
          </div>

          {settingsError && (
            <div className="p-3.5 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{settingsError}</span>
            </div>
          )}

          {settingsSuccess && (
            <div className="p-3.5 bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs rounded-xl flex items-center gap-2.5">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{settingsSuccess}</span>
            </div>
          )}

          <div className="divide-y divide-slate-800/80">
            {/* Exam Reminders */}
            <div className="py-4 flex items-center justify-between gap-4">
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-slate-200">Exam Reminders</span>
                <p className="text-[11px] text-slate-400">
                  Receive alerts about upcoming scheduled examinations and deadlines.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleTogglePreference('exam_reminders')}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out shrink-0 ${
                  notificationSettings.exam_reminders ? 'bg-indigo-600' : 'bg-slate-800'
                }`}
              >
                <div
                  className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                    notificationSettings.exam_reminders ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Result Notifications */}
            <div className="py-4 flex items-center justify-between gap-4">
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-slate-200">Result Notifications</span>
                <p className="text-[11px] text-slate-400">
                  Receive notifications when examination scores and evaluations are published.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleTogglePreference('result_notifications')}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out shrink-0 ${
                  notificationSettings.result_notifications ? 'bg-indigo-600' : 'bg-slate-800'
                }`}
              >
                <div
                  className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                    notificationSettings.result_notifications ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Integrity Alerts */}
            <div className="py-4 flex items-center justify-between gap-4">
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-slate-200">Integrity & Proctoring Alerts</span>
                <p className="text-[11px] text-slate-400">
                  Receive alerts concerning proctoring reviews and integrity assessments.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleTogglePreference('integrity_alerts')}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out shrink-0 ${
                  notificationSettings.integrity_alerts ? 'bg-indigo-600' : 'bg-slate-800'
                }`}
              >
                <div
                  className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                    notificationSettings.integrity_alerts ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* System Updates */}
            <div className="py-4 flex items-center justify-between gap-4">
              <div className="space-y-0.5">
                <span className="text-xs font-bold text-slate-200">System Updates</span>
                <p className="text-[11px] text-slate-400">
                  Receive announcements regarding platform maintenance and new feature updates.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleTogglePreference('system_updates')}
                className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors duration-200 ease-in-out shrink-0 ${
                  notificationSettings.system_updates ? 'bg-indigo-600' : 'bg-slate-800'
                }`}
              >
                <div
                  className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform duration-200 ease-in-out ${
                    notificationSettings.system_updates ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* SECTION 3: ACCOUNT & SESSION OVERVIEW */}
        {currentUser && (
          <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4 shadow-xl">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
              <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                <Shield className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">Account Overview</h3>
                <p className="text-xs text-slate-400">Core identity and security credentials.</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-xs">
              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Account Identifier</span>
                <p className="font-mono text-slate-300 truncate text-[11px]">{currentUser.id}</p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Authentication Mode</span>
                <p className="font-semibold text-slate-200">HttpOnly Cookie JWT</p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Account Created</span>
                <p className="font-semibold text-slate-200">
                  {currentUser.created_at
                    ? new Date(currentUser.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })
                    : 'N/A'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
