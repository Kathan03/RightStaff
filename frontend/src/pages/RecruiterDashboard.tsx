import React, { useState } from 'react';
import { JobForm } from '../components/recruiter/JobForm';
import { CandidateRanking } from '../components/recruiter/CandidateRanking';
import { Chatbot } from '../components/recruiter/Chatbot';
import { jobsApi } from '../api/jobs';
import { useRecruiterStore } from '../store/recruiterStore';
import { Loading } from '../components/shared/Loading';
import { AlertCircle, Sparkles } from 'lucide-react';

type View = 'create' | 'rank';

export const RecruiterDashboard: React.FC = () => {
  const [view, setView] = useState<View>('create');
  const [error, setError] = useState<string | null>(null);
  const { selectedJobId, rankedCandidates, isLoading, setSelectedJobId, setRankedCandidates, setLoading } =
    useRecruiterStore();

  const handleJobCreated = async (jobId: string) => {
    setSelectedJobId(jobId);
    setView('rank');
    await loadRankings(jobId);
  };

  const loadRankings = async (jobId: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await jobsApi.rankCandidates(jobId, true);
      setRankedCandidates(response.ranked_candidates);
    } catch (err: any) {
      const message =
        err.response?.data?.detail ||
        'Failed to load rankings. Make sure candidates have applied to this job.';
      setError(message);
      setRankedCandidates([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshRankings = () => {
    if (selectedJobId) {
      loadRankings(selectedJobId);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Recruiter Dashboard</h1>
              <p className="text-gray-600 mt-1">Manage jobs and find the best candidates</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setView('create')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  view === 'create'
                    ? 'bg-primary-600 text-white shadow-md'
                    : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
                }`}
              >
                Create Job
              </button>
              <button
                onClick={() => setView('rank')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  view === 'rank'
                    ? 'bg-primary-600 text-white shadow-md'
                    : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
                }${!selectedJobId ? ' opacity-50 cursor-not-allowed' : ''}`}
                disabled={!selectedJobId}
              >
                View Rankings
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {view === 'create' && <JobForm onSuccess={handleJobCreated} />}

        {view === 'rank' && selectedJobId && (
          <>
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-red-800 text-sm">{error}</p>
                  <button
                    onClick={handleRefreshRankings}
                    className="mt-2 text-sm text-red-700 underline hover:text-red-800"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            )}

            {isLoading ? (
              <div className="card">
                <Loading message="Ranking candidates..." />
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left: Rankings */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-primary-600" />
                      <h2 className="text-xl font-bold text-gray-900">AI-Ranked Candidates</h2>
                    </div>
                    <button
                      onClick={handleRefreshRankings}
                      className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Refresh
                    </button>
                  </div>
                  <CandidateRanking
                    candidates={rankedCandidates}
                    onSelectCandidate={(c) => console.log('Selected:', c)}
                  />
                </div>

                {/* Right: Chatbot */}
                <div>
                  <Chatbot jobId={selectedJobId} />
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
