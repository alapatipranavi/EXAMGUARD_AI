'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  CSVImportParseResponse,
  PDFImportParseResponse,
  QuestionCreateInput,
  questionImportAPI,
} from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import { FileSpreadsheet, FileText, Upload, CheckCircle2, XCircle, ArrowLeft, Check, Download, Info } from 'lucide-react';

export default function QuestionImportPage() {
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<'CSV' | 'PDF'>('CSV');
  const [parsing, setParsing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // CSV States
  const [csvResult, setCsvResult] = useState<CSVImportParseResponse | null>(null);

  // PDF States
  const [pdfResult, setPdfResult] = useState<PDFImportParseResponse | null>(null);

  const handleDownloadTemplate = () => {
    const templateContent =
      "question_text,subject,topic,question_type,difficulty,marks,negative_marks,option_a,option_b,option_c,option_d,correct_options,explanation,model_answer\n" +
      '"What is the primary purpose of a DBMS?",DBMS,Introduction,MCQ,EASY,1,0,"Store and manage data","Compile source code","Design networks","Create operating systems",A,"A DBMS provides systematic data storage and management.",\n' +
      '"Explain the ACID properties in database systems.",DBMS,Transactions,SHORT_ANSWER,MEDIUM,3,0,,,,,, "ACID stands for Atomicity Consistency Isolation Durability.",\n';

    const blob = new Blob([templateContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'examguard_question_template.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setParsing(true);
    try {
      const res = await questionImportAPI.parseCSV(file);
      setCsvResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'CSV parsing failed.');
    } finally {
      setParsing(false);
    }
  };

  const handlePDFUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setParsing(true);
    try {
      const res = await questionImportAPI.parsePDF(file);
      setPdfResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'PDF parsing failed.');
    } finally {
      setParsing(false);
    }
  };

  const handleConfirmCSVImport = async () => {
    if (!csvResult) return;
    const validQuestions: QuestionCreateInput[] = csvResult.rows
      .filter((r) => r.is_valid && r.question)
      .map((r) => r.question!);

    if (validQuestions.length === 0) {
      setError('No valid questions found to import.');
      return;
    }

    setConfirming(true);
    setError(null);
    try {
      await questionImportAPI.confirmImport({
        source: 'CSV_IMPORT',
        questions: validQuestions,
      });
      router.push('/question-bank');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to import CSV questions.');
    } finally {
      setConfirming(false);
    }
  };

  const handleConfirmPDFImport = async () => {
    if (!pdfResult) return;
    const validQuestions: QuestionCreateInput[] = pdfResult.items
      .filter((item) => item.is_valid && item.extracted_text)
      .map((item) => ({
        question_text: item.extracted_text,
        subject: item.detected_subject || 'General',
        question_type: item.detected_type,
        difficulty: item.detected_difficulty,
        source: 'PDF_IMPORT',
        marks: item.detected_marks || 2.0,
        options: item.detected_options.length > 0 ? item.detected_options : undefined,
      }));

    if (validQuestions.length === 0) {
      setError('No valid questions extracted from PDF.');
      return;
    }

    setConfirming(true);
    setError(null);
    try {
      await questionImportAPI.confirmImport({
        source: 'PDF_IMPORT',
        questions: validQuestions,
      });
      router.push('/question-bank');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to import PDF questions.');
    } finally {
      setConfirming(false);
    }
  };

  return (
    <AppShell title="Import Questions" allowedRoles={['EXAMINER']}>
      <PageHeader
        title="Import Questions 📥"
        subtitle="Upload CSV spreadsheet or PDF documents to parse, validate, preview, and import questions."
        actions={
          <button
            onClick={() => router.push('/question-bank')}
            className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" /> Question Bank
          </button>
        }
      />

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-4 text-xs font-bold">
        <button
          onClick={() => {
            setActiveTab('CSV');
            setError(null);
          }}
          className={`pb-3 border-b-2 flex items-center gap-2 transition ${
            activeTab === 'CSV'
              ? 'border-emerald-500 text-emerald-400'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" /> CSV Import
        </button>

        <button
          onClick={() => {
            setActiveTab('PDF');
            setError(null);
          }}
          className={`pb-3 border-b-2 flex items-center gap-2 transition ${
            activeTab === 'PDF'
              ? 'border-amber-500 text-amber-400'
              : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          <FileText className="w-4 h-4" /> PDF Import
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs">
          {error}
        </div>
      )}

      {/* CSV TAB */}
      {activeTab === 'CSV' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Upload Area */}
            <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white">Upload CSV File</h3>
                <button
                  onClick={handleDownloadTemplate}
                  className="px-3.5 py-1.5 bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/30 text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" /> Download CSV Template
                </button>
              </div>

              <p className="text-xs text-slate-400 leading-relaxed">
                Upload your questions in CSV format. Questions will be parsed, validated, and previewed before being saved into your Question Bank.
              </p>

              <div className="border-2 border-dashed border-slate-800 hover:border-emerald-500/50 rounded-2xl p-8 text-center bg-slate-950/60 transition">
                <Upload className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                <p className="text-xs text-slate-300 font-semibold mb-3">
                  {parsing ? 'Parsing CSV File...' : 'Select or drop your CSV file here'}
                </p>
                <input
                  type="file"
                  accept=".csv"
                  disabled={parsing}
                  onChange={handleCSVUpload}
                  className="block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-emerald-600 file:text-white hover:file:bg-emerald-500 cursor-pointer max-w-xs mx-auto"
                />
              </div>
            </div>

            {/* User Guidance Format Card */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm space-y-3 text-xs">
              <div className="flex items-center gap-2 text-emerald-400 font-bold">
                <Info className="w-4 h-4" /> CSV Format Guidance
              </div>

              <div className="space-y-2 text-slate-300">
                <p className="font-semibold text-white">Required Fields:</p>
                <ul className="list-disc list-inside space-y-1 text-slate-400 font-mono text-[11px]">
                  <li>question_text</li>
                  <li>subject</li>
                  <li>question_type (MCQ, MULTI_SELECT, SHORT_ANSWER...)</li>
                  <li>difficulty (EASY, MEDIUM, HARD)</li>
                  <li>marks (&gt; 0)</li>
                </ul>

                <p className="font-semibold text-white pt-2">Correct Options Format:</p>
                <ul className="space-y-1 text-slate-400 font-mono text-[11px]">
                  <li>MCQ: <code className="text-emerald-300 bg-slate-950 px-1 rounded">A</code> (exactly 1)</li>
                  <li>MULTI_SELECT: <code className="text-emerald-300 bg-slate-950 px-1 rounded">A|C</code> (at least 2)</li>
                </ul>
              </div>
            </div>
          </div>

          {/* CSV Preview Table */}
          {csvResult && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm text-xs">
                <div>
                  <span className="font-bold text-white">Total Rows: {csvResult.total_rows}</span> |{' '}
                  <span className="text-emerald-400 font-bold">Valid: {csvResult.valid_rows_count}</span> |{' '}
                  <span className="text-red-400 font-bold">Invalid: {csvResult.invalid_rows_count}</span>
                </div>

                <button
                  onClick={handleConfirmCSVImport}
                  disabled={confirming || csvResult.valid_rows_count === 0}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-emerald-600/20 flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Check className="w-4 h-4" />
                  {confirming ? 'Importing...' : `Import Valid Questions (${csvResult.valid_rows_count})`}
                </button>
              </div>

              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden text-xs">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-950/60 border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      <th className="py-3 px-4">Row #</th>
                      <th className="py-3 px-4">Question</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Subject</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4">Validation Detail</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {csvResult.rows.map((row) => (
                      <tr key={row.row_number} className={row.is_valid ? 'hover:bg-slate-950/40' : 'bg-red-950/20'}>
                        <td className="py-3 px-4 font-mono font-bold text-slate-400">#{row.row_number}</td>
                        <td className="py-3 px-4 max-w-sm font-medium text-white">
                          {row.question?.question_text || row.raw_data['question_text'] || 'Empty'}
                        </td>
                        <td className="py-3 px-4 font-mono text-indigo-300">
                          {row.question?.question_type || row.raw_data['question_type'] || 'N/A'}
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {row.question?.subject || row.raw_data['subject'] || 'N/A'}
                        </td>
                        <td className="py-3 px-4 text-center whitespace-nowrap">
                          {row.is_valid ? (
                            <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800/60 inline-flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> Valid
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-red-950 text-red-300 border border-red-800/60 inline-flex items-center gap-1">
                              <XCircle className="w-3 h-3" /> Invalid
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {row.is_valid ? 'Ready to import' : row.error_message}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* PDF TAB */}
      {activeTab === 'PDF' && (
        <div className="space-y-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="text-sm font-bold text-white">Upload PDF Document</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Upload a question paper PDF document. ExamGuard AI will safely extract text-based questions for Examiner review.
            </p>

            <div className="border-2 border-dashed border-slate-800 hover:border-amber-500/50 rounded-2xl p-8 text-center bg-slate-950/60 transition">
              <Upload className="w-8 h-8 text-amber-400 mx-auto mb-2" />
              <p className="text-xs text-slate-300 font-semibold mb-3">
                {parsing ? 'Parsing PDF Document...' : 'Select or drop your PDF document here'}
              </p>
              <input
                type="file"
                accept=".pdf"
                disabled={parsing}
                onChange={handlePDFUpload}
                className="block w-full text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-amber-600 file:text-white hover:file:bg-amber-500 cursor-pointer max-w-xs mx-auto"
              />
            </div>
          </div>

          {/* PDF Preview Items */}
          {pdfResult && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm text-xs">
                <div className="space-y-1">
                  <p className="font-bold text-white">Extracted Questions: {pdfResult.total_extracted}</p>
                  <p className="text-[11px] text-amber-300 italic">
                    Correct answer requires examiner review. Do not invent correct answers.
                  </p>
                </div>

                <button
                  onClick={handleConfirmPDFImport}
                  disabled={confirming || pdfResult.total_extracted === 0}
                  className="px-5 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-amber-600/20 flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Check className="w-4 h-4" />
                  {confirming ? 'Importing...' : `Confirm & Import (${pdfResult.total_extracted})`}
                </button>
              </div>

              <div className="space-y-3">
                {pdfResult.items.map((item) => (
                  <div key={item.item_number} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-400">Item #{item.item_number}</span>
                      {item.needs_review ? (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-950 text-amber-300 border border-amber-800/60">
                          Correct answer requires examiner review
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800/60">
                          Detected Answer ({item.detected_answer})
                        </span>
                      )}
                    </div>
                    <p className="font-semibold text-white leading-relaxed">{item.extracted_text}</p>

                    {item.detected_options.length > 0 && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                        {item.detected_options.map((opt, oIdx) => (
                          <div key={oIdx} className="p-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-300">
                            {opt.option_text} {opt.is_correct && '✓'}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </AppShell>
  );
}
