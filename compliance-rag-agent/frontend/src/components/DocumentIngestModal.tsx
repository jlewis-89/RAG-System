import React, { useState } from 'react';
import { X, Upload, FileText, CheckCircle2, AlertCircle } from 'lucide-react';
import api from '../services/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const DocumentIngestModal: React.FC<Props> = ({ isOpen, onClose, onSuccess }) => {
  const [title, setTitle] = useState('');
  const [standardCode, setStandardCode] = useState('ISO-9001');
  const [content, setContent] = useState('');
  const [sourceIdentifier, setSourceIdentifier] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !standardCode || !content) {
      setFeedback({ type: 'error', message: 'Please fill in Title, Standard Code, and Document Content.' });
      return;
    }

    try {
      setIsSubmitting(true);
      setFeedback(null);
      const res = await api.ingestDocument({
        title,
        standard_code: standardCode,
        content,
        source_identifier: sourceIdentifier || `${standardCode.toLowerCase()}_manual_upload.txt`,
      });

      setFeedback({
        type: 'success',
        message: `Indexed "${res.title}" with ${res.total_chunks} chunks into ChromaDB.`
      });
      setTitle('');
      setContent('');
      setSourceIdentifier('');
      setTimeout(() => {
        onSuccess();
        onClose();
        setFeedback(null);
      }, 1500);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        message: err.response?.data?.error || err.message || 'Failed to ingest document.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-xl glass-panel rounded-2xl border border-slate-700 shadow-2xl p-6">
        
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Ingest Standard Document</h2>
              <p className="text-xs text-slate-400">Process clauses and persist embeddings into ChromaDB</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {feedback && (
          <div
            className={`mt-4 p-3 rounded-xl flex items-center gap-2 text-xs font-medium border ${
              feedback.type === 'success'
                ? 'bg-emerald-950/50 text-emerald-300 border-emerald-700/50'
                : 'bg-rose-950/50 text-rose-300 border-rose-700/50'
            }`}
          >
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Standard Code (e.g. ISO-9001, ASME-VIII)
              </label>
              <input
                type="text"
                value={standardCode}
                onChange={(e) => setStandardCode(e.target.value.toUpperCase())}
                placeholder="ASME-VIII"
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Document Title
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Pressure Vessel Design Guidelines"
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Source Identifier (Optional)
            </label>
            <input
              type="text"
              value={sourceIdentifier}
              onChange={(e) => setSourceIdentifier(e.target.value)}
              placeholder="asme_sec_viii_div1_2023.pdf"
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Document Text / Clause Content
            </label>
            <textarea
              rows={6}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste regulatory clauses, engineering requirements, or standards text here (e.g., Clause 4.1.2 The organization shall...)..."
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono resize-none"
              required
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-semibold text-xs transition shadow-lg shadow-emerald-600/20 disabled:opacity-50"
            >
              <FileText className="w-4 h-4" />
              <span>{isSubmitting ? 'Embedding & Indexing...' : 'Index in ChromaDB'}</span>
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};
