import React, { useState, useEffect } from 'react';
import { JobForm } from '../components/recruiter/JobForm';
import { CandidateRanking } from '../components/recruiter/CandidateRanking';
import { Chatbot } from '../components/recruiter/Chatbot';
import { jobsApi } from '../api/jobs';
import { useRecruiterStore } from '../store/recruiterStore';
import { Loading } from '../components/shared/Loading';
import { Job, Applicant } from '../types';
import { AlertCircle, Sparkles, Plus, Briefcase, MapPin, Calendar, Users, ArrowLeft, Mail, Phone, Clock } from 'lucide-react';

type View = 'list' | 'create' | 'detail';
type DetailTab = 'rankings' | 'applicants';

export const RecruiterDashboard: React.FC = () => {
  const [view, setView] = useState<View>('list');
  const [detailTab, setDetailTab] = useState<DetailTab>('rankings');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [loadingApplicants, setLoadingApplicants] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { selectedJobId, rankedCandidates, isLoading, setSelectedJobId, setRankedCandidates, setLoading } =
    useRecruiterStore();

  // Load all jobs on mount
  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    setLoadingJobs(true);
    try {
      const data = await jobsApi.getAllJobs();
      setJobs(data);
    } catch (err) {
      console.error('Failed to load jobs:', err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const handleJobCreated = async (jobId: string) => {
    await loadJobs(); // Reload jobs
    setSelectedJobId(jobId);
    setView('detail');
    await loadRankings(jobId);
    await loadApplicants(jobId);
  };

  const handleSelectJob = async (job: Job) => {
    setSelectedJobId(job.id);
    setView('detail');
    await loadRankings(job.id);
    await loadApplicants(job.id);
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

  const loadApplicants = async (jobId: string) => {
    setLoadingApplicants(true);
    try {
      const response = await jobsApi.getApplicants(jobId);
      setApplicants(response.applicants);
    } catch (err) {
      console.error('Failed to load applicants:', err);
      setApplicants([]);
    } finally {
      setLoadingApplicants(false);
    }
  };

  const handleRefreshRankings = () => {
    if (selectedJobId) {
      loadRankings(selectedJobId);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Recently posted';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const selectedJob = jobs.find((j) => j.id === selectedJobId);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {view !== 'list' && (
                <button
                  onClick={() => {
                    setView('list');
                    setSelectedJobId(null);
                  }}
                  className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ArrowLeft className="w-5 h-5 text-gray-600" />
                </button>
              )}
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  {view === 'list'
                    ? 'Recruiter Dashboard'
                    : view === 'create'
                    ? 'Create New Job'
                    : selectedJob?.title || 'Job Details'}
                </h1>
                <p className="text-gray-600 mt-1">
                  {view === 'list'
                    ? 'Manage jobs and find the best candidates'
                    : view === 'create'
                    ? 'Post a new position to find candidates'
                    : 'View rankings and applicants'}
                </p>
              </div>
            </div>
            {view === 'list' && (
              <button
                onClick={() => setView('create')}
                className="btn-primary flex items-center gap-2"
              >
                <Plus className="w-5 h-5" />
                Create Job
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Job List View */}
        {view === 'list' && (
          <>
            {loadingJobs ? (
              <Loading message="Loading jobs..." />
            ) : jobs.length === 0 ? (
              <div className="card text-center py-16">
                <Briefcase className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-gray-900 mb-2">No Jobs Yet</h2>
                <p className="text-gray-600 mb-6">
                  Create your first job posting to start finding candidates
                </p>
                <button
                  onClick={() => setView('create')}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  <Plus className="w-5 h-5" />
                  Create Job
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {jobs.map((job) => (
                  <div
                    key={job.id}
                    onClick={() => handleSelectJob(job)}
                    className="card cursor-pointer hover:shadow-lg transition-all duration-200 border-2 border-transparent hover:border-primary-200"
                  >
                    <div className="flex justify-between items-start mb-4">
                      <h3 className="font-semibold text-lg text-gray-900 line-clamp-1">
                        {job.title}
                      </h3>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          job.status === 'open'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {job.status}
                      </span>
                    </div>

                    <div className="space-y-2 text-sm text-gray-600 mb-4">
                      {job.location && (
                        <div className="flex items-center gap-2">
                          <MapPin className="w-4 h-4" />
                          <span>{job.location}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        <span>Posted {formatDate(job.created_at)}</span>
                      </div>
                    </div>

                    <p className="text-sm text-gray-600 line-clamp-2 mb-4">
                      {job.description}
                    </p>

                    <div className="flex flex-wrap gap-1.5 mb-4">
                      {job.required_skills.slice(0, 4).map((skill) => (
                        <span
                          key={skill}
                          className="px-2 py-0.5 bg-primary-100 text-primary-700 rounded text-xs"
                        >
                          {skill}
                        </span>
                      ))}
                      {job.required_skills.length > 4 && (
                        <span className="px-2 py-0.5 text-gray-500 text-xs">
                          +{job.required_skills.length - 4}
                        </span>
                      )}
                    </div>

                    <div className="pt-4 border-t border-gray-100">
                      <button className="w-full btn-primary text-sm flex items-center justify-center gap-2">
                        <Users className="w-4 h-4" />
                        View Candidates
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Create Job View */}
        {view === 'create' && <JobForm onSuccess={handleJobCreated} />}

        {/* Job Detail View - Rankings, Applicants & Chatbot */}
        {view === 'detail' && selectedJobId && (
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

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: Tabs for Rankings/Applicants */}
              <div>
                {/* Tab Headers */}
                <div className="flex gap-2 mb-4">
                  <button
                    onClick={() => setDetailTab('rankings')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                      detailTab === 'rankings'
                        ? 'bg-primary-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
                    }`}
                  >
                    <Sparkles className="w-4 h-4" />
                    AI Rankings ({rankedCandidates.length})
                  </button>
                  <button
                    onClick={() => setDetailTab('applicants')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                      detailTab === 'applicants'
                        ? 'bg-primary-600 text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
                    }`}
                  >
                    <Users className="w-4 h-4" />
                    All Applicants ({applicants.length})
                  </button>
                </div>

                {/* Tab Content */}
                {detailTab === 'rankings' && (
                  <>
                    {isLoading ? (
                      <div className="card">
                        <Loading message="Ranking candidates..." />
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between mb-4">
                          <h2 className="text-xl font-bold text-gray-900">AI-Ranked Candidates</h2>
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
                      </>
                    )}
                  </>
                )}

                {detailTab === 'applicants' && (
                  <>
                    {loadingApplicants ? (
                      <div className="card">
                        <Loading message="Loading applicants..." />
                      </div>
                    ) : applicants.length === 0 ? (
                      <div className="card text-center py-12">
                        <Users className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">No Applicants Yet</h3>
                        <p className="text-gray-600">
                          Candidates will appear here once they apply to this job.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <h2 className="text-xl font-bold text-gray-900">All Applicants</h2>
                        {applicants.map((applicant) => (
                          <div key={applicant.application_id} className="card">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <h4 className="text-lg font-semibold text-gray-900 mb-2">
                                  {applicant.full_name}
                                </h4>

                                <div className="space-y-1 text-sm text-gray-600 mb-3">
                                  {applicant.email && (
                                    <div className="flex items-center gap-2">
                                      <Mail className="w-4 h-4" />
                                      <span>{applicant.email}</span>
                                    </div>
                                  )}
                                  {applicant.phone && (
                                    <div className="flex items-center gap-2">
                                      <Phone className="w-4 h-4" />
                                      <span>{applicant.phone}</span>
                                    </div>
                                  )}
                                  {applicant.location && (
                                    <div className="flex items-center gap-2">
                                      <MapPin className="w-4 h-4" />
                                      <span>{applicant.location}</span>
                                    </div>
                                  )}
                                  {applicant.years_experience && (
                                    <div className="flex items-center gap-2">
                                      <Clock className="w-4 h-4" />
                                      <span>{applicant.years_experience} years experience</span>
                                    </div>
                                  )}
                                </div>

                                {applicant.professional_summary && (
                                  <p className="text-sm text-gray-700 line-clamp-2">
                                    {applicant.professional_summary}
                                  </p>
                                )}
                              </div>

                              <div className="ml-4 text-right">
                                <span
                                  className={`px-2 py-1 rounded-full text-xs font-medium ${
                                    applicant.status === 'applied'
                                      ? 'bg-blue-100 text-blue-700'
                                      : applicant.status === 'interviewed'
                                      ? 'bg-yellow-100 text-yellow-700'
                                      : applicant.status === 'hired'
                                      ? 'bg-green-100 text-green-700'
                                      : 'bg-gray-100 text-gray-600'
                                  }`}
                                >
                                  {applicant.status}
                                </span>
                                <p className="text-xs text-gray-500 mt-2">
                                  Applied {formatDate(applicant.applied_at)}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Right: Chatbot */}
              <div>
                <Chatbot jobId={selectedJobId} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
