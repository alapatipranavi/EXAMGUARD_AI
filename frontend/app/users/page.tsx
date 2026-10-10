'use client';

import React, { useState, useEffect, useCallback } from 'react';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import {
  Users,
  UserPlus,
  Search,
  Filter,
  Shield,
  UserCheck,
  UserX,
  Edit,
  Loader2,
  AlertCircle,
  CheckCircle2,
  X,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  Building2,
} from 'lucide-react';
import { adminAPI, academicAPI, User, AdminUserCreateInput, College, Department, Section } from '@/lib/api';

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Pagination & Filtering
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Create User Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createForm, setCreateForm] = useState<AdminUserCreateInput>({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    role: 'EXAMINER',
  });

  // Edit Role Modal State
  const [roleModalUser, setRoleModalUser] = useState<User | null>(null);
  const [selectedRole, setSelectedRole] = useState<'STUDENT' | 'EXAMINER'>('STUDENT');
  const [roleLoading, setRoleLoading] = useState(false);

  // Toggle Status Modal State
  const [statusModalUser, setStatusModalUser] = useState<User | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  // Academic Assignment Modal State
  const [academicModalUser, setAcademicModalUser] = useState<User | null>(null);
  const [collegesList, setCollegesList] = useState<College[]>([]);
  const [deptsList, setDeptsList] = useState<Department[]>([]);
  const [sectionsList, setSectionsList] = useState<Section[]>([]);
  const [academicCollegeId, setAcademicCollegeId] = useState<string>('');
  const [academicDeptId, setAcademicDeptId] = useState<string>('');
  const [academicYear, setAcademicYear] = useState<number>(1);
  const [academicSectionId, setAcademicSectionId] = useState<string>('');
  const [academicLoading, setAcademicLoading] = useState(false);

  const openAcademicModal = async (u: User) => {
    setAcademicModalUser(u);
    setAcademicCollegeId(u.college_id || '');
    setAcademicDeptId(u.department_id || '');
    setAcademicYear(u.year_of_study || 1);
    setAcademicSectionId(u.section_id || '');
    try {
      const cols = await academicAPI.getPublicColleges();
      setCollegesList(cols);
      if (u.college_id) {
        const depts = await academicAPI.getPublicDepartments(u.college_id);
        setDeptsList(depts);
      } else {
        setDeptsList([]);
      }
      if (u.department_id) {
        const secs = await academicAPI.getPublicSections(u.department_id, u.year_of_study || 1);
        setSectionsList(secs);
      } else {
        setSectionsList([]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCollegeChangeInModal = async (colId: string) => {
    setAcademicCollegeId(colId);
    setAcademicDeptId('');
    setAcademicSectionId('');
    if (colId) {
      const depts = await academicAPI.getPublicDepartments(colId);
      setDeptsList(depts);
    } else {
      setDeptsList([]);
    }
  };

  const handleDeptChangeInModal = async (deptId: string) => {
    setAcademicDeptId(deptId);
    setAcademicSectionId('');
    if (deptId) {
      const secs = await academicAPI.getPublicSections(deptId, academicYear);
      setSectionsList(secs);
    } else {
      setSectionsList([]);
    }
  };

  const handleYearChangeInModal = async (year: number) => {
    setAcademicYear(year);
    setAcademicSectionId('');
    if (academicDeptId) {
      const secs = await academicAPI.getPublicSections(academicDeptId, year);
      setSectionsList(secs);
    }
  };

  const handleSaveAcademicAssignment = async () => {
    if (!academicModalUser) return;
    setAcademicLoading(true);
    try {
      if (academicModalUser.role === 'EXAMINER') {
        await academicAPI.updateUserCollege(academicModalUser.id, academicCollegeId || null);
        showToast(`Updated college assignment for Examiner.`);
      } else if (academicModalUser.role === 'STUDENT') {
        await academicAPI.updateStudentAcademicProfile(academicModalUser.id, {
          college_id: academicCollegeId || null,
          department_id: academicDeptId || null,
          year_of_study: academicYear || null,
          section_id: academicSectionId || null,
        });
        showToast(`Updated academic profile for Student.`);
      }
      setAcademicModalUser(null);
      fetchUsers();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to save academic assignment', 'error');
    } finally {
      setAcademicLoading(false);
    }
  };

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const is_active_param = statusFilter === '' ? undefined : statusFilter === 'true';
      const res = await adminAPI.getUsers({
        page,
        page_size: pageSize,
        search: search || undefined,
        role: roleFilter || undefined,
        is_active: is_active_param,
      });
      setUsers(res.items);
      setTotalPages(res.pages || 1);
      setTotalUsers(res.total || 0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, roleFilter, statusFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      const newObj = await adminAPI.createUser(createForm);
      showToast(`User ${newObj.first_name} ${newObj.last_name} created successfully.`);
      setIsCreateModalOpen(false);
      setCreateForm({
        first_name: '',
        last_name: '',
        email: '',
        password: '',
        role: 'EXAMINER',
      });
      fetchUsers();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to create user', 'error');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleRoleUpdate = async () => {
    if (!roleModalUser) return;
    setRoleLoading(true);
    try {
      const updated = await adminAPI.updateUserRole(roleModalUser.id, selectedRole);
      showToast(`Updated role for ${updated.first_name} ${updated.last_name} to ${updated.role}.`);
      setRoleModalUser(null);
      fetchUsers();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to update user role', 'error');
    } finally {
      setRoleLoading(false);
    }
  };

  const handleStatusToggle = async () => {
    if (!statusModalUser) return;
    setStatusLoading(true);
    try {
      const newStatus = !statusModalUser.is_active;
      const updated = await adminAPI.updateUserStatus(statusModalUser.id, newStatus);
      showToast(`User ${updated.first_name} ${updated.last_name} is now ${updated.is_active ? 'Active' : 'Inactive'}.`);
      setStatusModalUser(null);
      fetchUsers();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : 'Failed to update user status', 'error');
    } finally {
      setStatusLoading(false);
    }
  };

  return (
    <AppShell allowedRoles={['ADMIN']}>
      <div className="space-y-6">
        <PageHeader
          title="User Management"
          subtitle="Provision, manage, and configure user accounts and roles across ExamGuard AI."
          actions={
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold text-xs transition flex items-center gap-2 shadow-lg shadow-indigo-600/20"
            >
              <UserPlus className="w-4 h-4" /> Provision User
            </button>
          }
        />

        {/* Toast Notification */}
        {toast && (
          <div
            className={`p-4 rounded-xl border flex items-center justify-between transition-all duration-300 ${
              toast.type === 'success'
                ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                : 'bg-red-950/80 border-red-800 text-red-300'
            }`}
          >
            <div className="flex items-center gap-3">
              {toast.type === 'success' ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
              )}
              <span className="text-sm font-medium">{toast.message}</span>
            </div>
            <button onClick={() => setToast(null)} className="text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Filters & Search Toolbar */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500 transition"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto justify-end">
            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs text-slate-400 font-medium">Role:</span>
              <select
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Roles</option>
                <option value="STUDENT">Student</option>
                <option value="EXAMINER">Examiner</option>
                <option value="ADMIN">Admin</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Statuses</option>
                <option value="true">Active</option>
                <option value="false">Inactive</option>
              </select>
            </div>
          </div>
        </div>

        {/* Users Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          {loading ? (
            <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
              <p className="text-xs">Loading user list...</p>
            </div>
          ) : error ? (
            <div className="p-8 text-center text-red-400 flex flex-col items-center gap-3">
              <ShieldAlert className="w-8 h-8 text-red-400" />
              <p className="text-sm font-semibold">{error}</p>
              <button
                onClick={fetchUsers}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs"
              >
                Retry
              </button>
            </div>
          ) : users.length === 0 ? (
            <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-2">
              <Users className="w-10 h-10 text-slate-600" />
              <p className="text-sm font-medium text-slate-300">No users found</p>
              <p className="text-xs text-slate-500">Try adjusting your search query or filters.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800 font-semibold">
                  <tr>
                    <th className="px-6 py-4">User</th>
                    <th className="px-6 py-4">Email</th>
                    <th className="px-6 py-4">Role</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Registered</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {users.map((user) => (
                    <tr key={user.id} className="hover:bg-slate-800/40 transition">
                      <td className="px-6 py-4 font-semibold text-slate-100">
                        {user.first_name} {user.last_name}
                      </td>
                      <td className="px-6 py-4 text-slate-300 font-mono text-[11px]">{user.email}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                            user.role === 'ADMIN'
                              ? 'bg-purple-950/60 border-purple-800 text-purple-300'
                              : user.role === 'EXAMINER'
                              ? 'bg-blue-950/60 border-blue-800 text-blue-300'
                              : 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
                          }`}
                        >
                          <Shield className="w-3 h-3" />
                          {user.role}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                            user.is_active
                              ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-400'
                              : 'bg-red-950/60 border-red-800/80 text-red-400'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              user.is_active ? 'bg-emerald-400' : 'bg-red-400'
                            }`}
                          />
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-[11px]">
                        {new Date(user.created_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {/* Role edit button - only for STUDENT or EXAMINER */}
                          {user.role !== 'ADMIN' && (
                            <>
                              <button
                                onClick={() => openAcademicModal(user)}
                                className="p-2 rounded-lg bg-slate-800 hover:bg-indigo-950 border border-slate-700 hover:border-indigo-700 text-slate-300 hover:text-indigo-300 transition flex items-center gap-1 text-[11px]"
                                title="Academic Assignment"
                              >
                                <Building2 className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => {
                                  setRoleModalUser(user);
                                  setSelectedRole(user.role as 'STUDENT' | 'EXAMINER');
                                }}
                                className="p-2 rounded-lg bg-slate-800 hover:bg-indigo-950 border border-slate-700 hover:border-indigo-700 text-slate-300 hover:text-indigo-300 transition"
                                title="Edit Role"
                              >
                                <Edit className="w-3.5 h-3.5" />
                              </button>
                            </>
                          )}

                          {/* Activate/Deactivate Toggle */}
                          {user.role !== 'ADMIN' && (
                            <button
                              onClick={() => setStatusModalUser(user)}
                              className={`p-2 rounded-lg border transition ${
                                user.is_active
                                  ? 'bg-slate-800 hover:bg-red-950 border-slate-700 hover:border-red-700 text-slate-300 hover:text-red-300'
                                  : 'bg-slate-800 hover:bg-emerald-950 border-slate-700 hover:border-emerald-700 text-slate-300 hover:text-emerald-300'
                              }`}
                              title={user.is_active ? 'Deactivate Account' : 'Activate Account'}
                            >
                              {user.is_active ? (
                                <UserX className="w-3.5 h-3.5" />
                              ) : (
                                <UserCheck className="w-3.5 h-3.5" />
                              )}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Footer */}
          {!loading && users.length > 0 && (
            <div className="px-6 py-4 bg-slate-950/60 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
              <div>
                Showing <span className="font-semibold text-slate-200">{users.length}</span> of{' '}
                <span className="font-semibold text-slate-200">{totalUsers}</span> users
              </div>
              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-2 rounded-lg bg-slate-900 border border-slate-800 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 text-slate-300 transition"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="px-3 py-1 font-semibold text-slate-300">
                  Page {page} of {totalPages}
                </span>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="p-2 rounded-lg bg-slate-900 border border-slate-800 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 text-slate-300 transition"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Provision User Modal */}
        {isCreateModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-6 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-2">
                  <UserPlus className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-lg font-bold text-white">Provision User</h3>
                </div>
                <button
                  onClick={() => setIsCreateModalOpen(false)}
                  className="text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                      First Name
                    </label>
                    <input
                      type="text"
                      required
                      value={createForm.first_name}
                      onChange={(e) => setCreateForm({ ...createForm, first_name: e.target.value })}
                      placeholder="John"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                      Last Name
                    </label>
                    <input
                      type="text"
                      required
                      value={createForm.last_name}
                      onChange={(e) => setCreateForm({ ...createForm, last_name: e.target.value })}
                      placeholder="Doe"
                      className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={createForm.email}
                    onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                    placeholder="user@examguard.ai"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={createForm.password}
                    onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
                    placeholder="Min 8 characters"
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Account Role
                  </label>
                  <select
                    value={createForm.role}
                    onChange={(e) =>
                      setCreateForm({ ...createForm, role: e.target.value as 'STUDENT' | 'EXAMINER' })
                    }
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  >
                    <option value="EXAMINER">Examiner</option>
                    <option value="STUDENT">Student</option>
                  </select>
                </div>

                <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setIsCreateModalOpen(false)}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createLoading}
                    className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
                  >
                    {createLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create Account'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Update Role Modal */}
        {roleModalUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-6 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-2">
                  <Edit className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-lg font-bold text-white">Update User Role</h3>
                </div>
                <button onClick={() => setRoleModalUser(null)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <p className="text-xs text-slate-300">
                  Change role for <span className="font-semibold text-white">{roleModalUser.first_name} {roleModalUser.last_name}</span> ({roleModalUser.email}).
                </p>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Select New Role
                  </label>
                  <select
                    value={selectedRole}
                    onChange={(e) => setSelectedRole(e.target.value as 'STUDENT' | 'EXAMINER')}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  >
                    <option value="STUDENT">Student</option>
                    <option value="EXAMINER">Examiner</option>
                  </select>
                </div>

                <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                  <button
                    onClick={() => setRoleModalUser(null)}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRoleUpdate}
                    disabled={roleLoading}
                    className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
                  >
                    {roleLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save Role'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Toggle Status Modal */}
        {statusModalUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-6 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-amber-400" />
                  <h3 className="text-lg font-bold text-white">Confirm Status Change</h3>
                </div>
                <button onClick={() => setStatusModalUser(null)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <p className="text-xs text-slate-300">
                  Are you sure you want to{' '}
                  <span className="font-bold text-white">
                    {statusModalUser.is_active ? 'deactivate' : 'activate'}
                  </span>{' '}
                  the account for{' '}
                  <span className="font-semibold text-white">
                    {statusModalUser.first_name} {statusModalUser.last_name}
                  </span>{' '}
                  ({statusModalUser.email})?
                </p>

                {statusModalUser.is_active && (
                  <p className="text-[11px] text-amber-400 bg-amber-950/40 border border-amber-800/50 p-3 rounded-xl">
                    Warning: Deactivated users will be immediately prevented from logging in or using API endpoints.
                  </p>
                )}

                <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                  <button
                    onClick={() => setStatusModalUser(null)}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleStatusToggle}
                    disabled={statusLoading}
                    className={`px-5 py-2.5 rounded-xl text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-50 ${
                      statusModalUser.is_active
                        ? 'bg-red-600 hover:bg-red-500'
                        : 'bg-emerald-600 hover:bg-emerald-500'
                    }`}
                  >
                    {statusLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : statusModalUser.is_active ? (
                      'Deactivate User'
                    ) : (
                      'Activate User'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        {/* Academic Assignment Modal */}
        {academicModalUser && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-lg font-bold text-white">
                    {academicModalUser.role === 'EXAMINER' ? 'Assign Examiner College' : 'Update Student Academic Profile'}
                  </h3>
                </div>
                <button onClick={() => setAcademicModalUser(null)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <p className="text-xs text-slate-300">
                  Target User: <span className="font-semibold text-white">{academicModalUser.first_name} {academicModalUser.last_name}</span> ({academicModalUser.email})
                </p>

                {/* College Select */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    College
                  </label>
                  <select
                    value={academicCollegeId}
                    onChange={(e) => handleCollegeChangeInModal(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">-- Unassigned (No College Scope) --</option>
                    {collegesList.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.code})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Student specific fields */}
                {academicModalUser.role === 'STUDENT' && (
                  <>
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                        Department
                      </label>
                      <select
                        value={academicDeptId}
                        onChange={(e) => handleDeptChangeInModal(e.target.value)}
                        disabled={!academicCollegeId}
                        className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500 disabled:opacity-40"
                      >
                        <option value="">-- Select Department --</option>
                        {deptsList.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name} ({d.code})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                          Year of Study
                        </label>
                        <select
                          value={academicYear}
                          onChange={(e) => handleYearChangeInModal(Number(e.target.value))}
                          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
                        >
                          <option value={1}>1st Year</option>
                          <option value={2}>2nd Year</option>
                          <option value={3}>3rd Year</option>
                          <option value={4}>4th Year</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                          Section
                        </label>
                        <select
                          value={academicSectionId}
                          onChange={(e) => setAcademicSectionId(e.target.value)}
                          disabled={!academicDeptId}
                          className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500 disabled:opacity-40"
                        >
                          <option value="">-- Select Section --</option>
                          {sectionsList.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.name} ({s.code})
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </>
                )}

                <div className="pt-4 flex items-center justify-end gap-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setAcademicModalUser(null)}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveAcademicAssignment}
                    disabled={academicLoading}
                    className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-2 disabled:opacity-50"
                  >
                    {academicLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save Academic Profile'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
