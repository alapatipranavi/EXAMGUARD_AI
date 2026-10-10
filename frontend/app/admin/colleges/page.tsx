'use client';

import React, { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import {
  College,
  Department,
  Section,
  academicAPI,
} from '@/lib/api';
import { Building2, Plus, Edit2, Check, X, Layers, Grid, ShieldAlert, Loader2 } from 'lucide-react';

export default function AdminCollegesPage() {
  const [colleges, setColleges] = useState<College[]>([]);
  const [selectedCollege, setSelectedCollege] = useState<College | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDepartment, setSelectedDepartment] = useState<Department | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // College Form Modal State
  const [showCollegeModal, setShowCollegeModal] = useState(false);
  const [editingCollege, setEditingCollege] = useState<College | null>(null);
  const [collegeName, setCollegeName] = useState('');
  const [collegeCode, setCollegeCode] = useState('');

  // Department Form Modal State
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);
  const [deptName, setDeptName] = useState('');
  const [deptCode, setDeptCode] = useState('');

  // Section Form Modal State
  const [showSectionModal, setShowSectionModal] = useState(false);
  const [editingSection, setEditingSection] = useState<Section | null>(null);
  const [sectionName, setSectionName] = useState('');
  const [sectionCode, setSectionCode] = useState('');
  const [sectionYear, setSectionYear] = useState<number>(1);

  useEffect(() => {
    loadColleges();
  }, []);

  useEffect(() => {
    if (selectedCollege) {
      loadDepartments(selectedCollege.id);
    } else {
      setDepartments([]);
      setSelectedDepartment(null);
      setSections([]);
    }
  }, [selectedCollege]);

  useEffect(() => {
    if (selectedDepartment) {
      loadSections(selectedDepartment.id);
    } else {
      setSections([]);
    }
  }, [selectedDepartment]);

  const loadColleges = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await academicAPI.listCollegesAdmin();
      setColleges(data);
      if (data.length > 0 && !selectedCollege) {
        setSelectedCollege(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load colleges');
    } finally {
      setLoading(false);
    }
  };

  const loadDepartments = async (collegeId: string) => {
    try {
      setError(null);
      const data = await academicAPI.listDepartmentsAdmin(collegeId);
      setDepartments(data);
      if (data.length > 0) {
        setSelectedDepartment(data[0]);
      } else {
        setSelectedDepartment(null);
        setSections([]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load departments');
    }
  };

  const loadSections = async (deptId: string) => {
    try {
      setError(null);
      const data = await academicAPI.listSectionsAdmin(deptId);
      setSections(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load sections');
    }
  };

  // --- College Actions ---
  const handleSaveCollege = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setError(null);
      setSuccess(null);
      if (editingCollege) {
        await academicAPI.updateCollege(editingCollege.id, {
          name: collegeName,
          code: collegeCode,
        });
        setSuccess('College updated successfully.');
      } else {
        await academicAPI.createCollege({
          name: collegeName,
          code: collegeCode,
        });
        setSuccess('College created successfully.');
      }
      setShowCollegeModal(false);
      loadColleges();
    } catch (err: any) {
      setError(err.message || 'Failed to save college');
    }
  };

  // --- Department Actions ---
  const handleSaveDepartment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCollege) return;
    try {
      setError(null);
      setSuccess(null);
      if (editingDept) {
        await academicAPI.updateDepartment(editingDept.id, {
          name: deptName,
          code: deptCode,
        });
        setSuccess('Department updated successfully.');
      } else {
        await academicAPI.createDepartment({
          college_id: selectedCollege.id,
          name: deptName,
          code: deptCode,
        });
        setSuccess('Department created successfully.');
      }
      setShowDeptModal(false);
      loadDepartments(selectedCollege.id);
    } catch (err: any) {
      setError(err.message || 'Failed to save department');
    }
  };

  // --- Section Actions ---
  const handleSaveSection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDepartment) return;
    try {
      setError(null);
      setSuccess(null);
      if (editingSection) {
        await academicAPI.updateSection(editingSection.id, {
          name: sectionName,
          code: sectionCode,
        });
        setSuccess('Section updated successfully.');
      } else {
        await academicAPI.createSection({
          department_id: selectedDepartment.id,
          year_of_study: sectionYear,
          name: sectionName,
          code: sectionCode,
        });
        setSuccess('Section created successfully.');
      }
      setShowSectionModal(false);
      loadSections(selectedDepartment.id);
    } catch (err: any) {
      setError(err.message || 'Failed to save section');
    }
  };

  return (
    <AppShell allowedRoles={['ADMIN']}>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <Building2 className="w-7 h-7 text-indigo-400" />
              Academic Structure & Institutions
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Manage Colleges, Departments, and Year/Section structures for exam targeting.
            </p>
          </div>

          <button
            onClick={() => {
              setEditingCollege(null);
              setCollegeName('');
              setCollegeCode('');
              setShowCollegeModal(true);
            }}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" />
            Add New College
          </button>
        </div>

        {/* Alerts */}
        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 text-sm flex items-center gap-2">
            <Check className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {/* Main 3-Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* COLUMN 1: Colleges */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Building2 className="w-5 h-5 text-indigo-400" />
                1. Colleges ({colleges.length})
              </h2>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-12 text-slate-500">
                <Loader2 className="w-6 h-6 animate-spin" />
              </div>
            ) : colleges.length === 0 ? (
              <p className="text-slate-500 text-xs text-center py-8">No colleges configured yet.</p>
            ) : (
              <div className="space-y-2">
                {colleges.map((col) => {
                  const isSelected = selectedCollege?.id === col.id;
                  return (
                    <div
                      key={col.id}
                      onClick={() => setSelectedCollege(col)}
                      className={`p-3.5 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                        isSelected
                          ? 'bg-indigo-600/20 border-indigo-500/50 text-white shadow-md'
                          : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:bg-slate-800/50'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm">{col.name}</span>
                          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-indigo-300 border border-slate-700">
                            {col.code}
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingCollege(col);
                          setCollegeName(col.name);
                          setCollegeCode(col.code);
                          setShowCollegeModal(true);
                        }}
                        className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
                        title="Edit College"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* COLUMN 2: Departments */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                2. Departments
              </h2>
              {selectedCollege && (
                <button
                  onClick={() => {
                    setEditingDept(null);
                    setDeptName('');
                    setDeptCode('');
                    setShowDeptModal(true);
                  }}
                  className="px-2.5 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-xs font-semibold rounded-lg border border-indigo-500/40 flex items-center gap-1 transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Dept
                </button>
              )}
            </div>

            {!selectedCollege ? (
              <p className="text-slate-500 text-xs text-center py-8">Select a college to view departments.</p>
            ) : departments.length === 0 ? (
              <p className="text-slate-500 text-xs text-center py-8">No departments in this college.</p>
            ) : (
              <div className="space-y-2">
                {departments.map((dept) => {
                  const isSelected = selectedDepartment?.id === dept.id;
                  return (
                    <div
                      key={dept.id}
                      onClick={() => setSelectedDepartment(dept)}
                      className={`p-3.5 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                        isSelected
                          ? 'bg-indigo-600/20 border-indigo-500/50 text-white shadow-md'
                          : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:bg-slate-800/50'
                      }`}
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm">{dept.name}</span>
                          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-800 text-indigo-300 border border-slate-700">
                            {dept.code}
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingDept(dept);
                          setDeptName(dept.name);
                          setDeptCode(dept.code);
                          setShowDeptModal(true);
                        }}
                        className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
                        title="Edit Department"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* COLUMN 3: Sections & Year Groups */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-semibold text-white flex items-center gap-2">
                <Grid className="w-5 h-5 text-indigo-400" />
                3. Sections & Year Groups
              </h2>
              {selectedDepartment && (
                <button
                  onClick={() => {
                    setEditingSection(null);
                    setSectionName('');
                    setSectionCode('');
                    setSectionYear(1);
                    setShowSectionModal(true);
                  }}
                  className="px-2.5 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 text-xs font-semibold rounded-lg border border-indigo-500/40 flex items-center gap-1 transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Section
                </button>
              )}
            </div>

            {!selectedDepartment ? (
              <p className="text-slate-500 text-xs text-center py-8">Select a department to view sections.</p>
            ) : sections.length === 0 ? (
              <p className="text-slate-500 text-xs text-center py-8">No sections created for this department.</p>
            ) : (
              <div className="space-y-4">
                {[1, 2, 3, 4].map((year) => {
                  const yearSections = sections.filter((s) => s.year_of_study === year);
                  if (yearSections.length === 0) return null;

                  return (
                    <div key={year} className="space-y-2">
                      <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 border-b border-slate-800/80 pb-1">
                        Year {year}
                      </h4>
                      <div className="grid grid-cols-1 gap-2">
                        {yearSections.map((sec) => (
                          <div
                            key={sec.id}
                            className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between text-slate-300"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-xs">{sec.name}</span>
                              <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-slate-900 text-slate-400 border border-slate-800">
                                {sec.code}
                              </span>
                            </div>

                            <button
                              onClick={() => {
                                setEditingSection(sec);
                                setSectionName(sec.name);
                                setSectionCode(sec.code);
                                setSectionYear(sec.year_of_study);
                                setShowSectionModal(true);
                              }}
                              className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* MODAL: College Create/Edit */}
        {showCollegeModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-lg font-bold text-white">
                  {editingCollege ? 'Edit College' : 'Create New College'}
                </h3>
                <button onClick={() => setShowCollegeModal(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveCollege} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">College Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. College of Engineering"
                    value={collegeName}
                    onChange={(e) => setCollegeName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">College Code</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. COE"
                    value={collegeCode}
                    onChange={(e) => setCollegeCode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 uppercase font-mono"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => setShowCollegeModal(false)}
                    className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-md transition"
                  >
                    Save College
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: Department Create/Edit */}
        {showDeptModal && selectedCollege && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-lg font-bold text-white">
                  {editingDept ? 'Edit Department' : `Create Department for ${selectedCollege.code}`}
                </h3>
                <button onClick={() => setShowDeptModal(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveDepartment} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Department Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Computer Science & Engineering"
                    value={deptName}
                    onChange={(e) => setDeptName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Department Code</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CSE"
                    value={deptCode}
                    onChange={(e) => setDeptCode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 uppercase font-mono"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => setShowDeptModal(false)}
                    className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-md transition"
                  >
                    Save Department
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* MODAL: Section Create/Edit */}
        {showSectionModal && selectedDepartment && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-lg font-bold text-white">
                  {editingSection ? 'Edit Section' : `Create Section for ${selectedDepartment.code}`}
                </h3>
                <button onClick={() => setShowSectionModal(false)} className="text-slate-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSaveSection} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Year of Study</label>
                  <select
                    value={sectionYear}
                    onChange={(e) => setSectionYear(Number(e.target.value))}
                    disabled={!!editingSection}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value={1}>1st Year</option>
                    <option value={2}>2nd Year</option>
                    <option value={3}>3rd Year</option>
                    <option value={4}>4th Year</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Section Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Section A"
                    value={sectionName}
                    onChange={(e) => setSectionName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Section Code</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. SEC-A"
                    value={sectionCode}
                    onChange={(e) => setSectionCode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 uppercase font-mono"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-3">
                  <button
                    type="button"
                    onClick={() => setShowSectionModal(false)}
                    className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-md transition"
                  >
                    Save Section
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
