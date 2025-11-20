import React, { useEffect, useState } from 'react';
import { candidatesApi } from '../../api/candidates';
import { Briefcase, MapPin, Clock, CheckCircle, AlertCircle, Calendar, ChevronRight } from 'lucide-react';
import { Job } from '../../types';
import { Loading } from '../shared/Loading';

interface JobListProps {
  candidateId: string;
}

export const JobList: React.FC<JobListProps> = ({ candidateId }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [applying, setApplying] = useState<string | null>(null);
  const [appliedJobs, setAppliedJobs] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    try {
      const data = await candidatesApi.getJobs();
      setJobs(data);
      // Auto-select first job
      if (data.length > 0) {
        setSelectedJob(data[0]);
      }
    } catch (err) {
      console.error('Failed to load jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async (jobId: string) => {
    setApplying(jobId);
    setMessage(null);

    try {
      await candidatesApi.applyToJob(jobId, candidateId);
      setAppliedJobs((prev) => new Set(prev).add(jobId));
      setMessage({ type: 'success', text: 'Application submitted successfully!' });
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || 'Application failed. Please try again.';
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setApplying(null);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Recently posted';
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return <Loading message="Loading available jobs..." />;
  }

  if (jobs.length === 0) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12">
        <Briefcase className="w-16 h-16 text-gray-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">No Jobs Available</h2>
        <p className="text-gray-600">
          There are currently no open positions. Please check back later.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Available Jobs</h2>
        <p className="text-gray-600 mt-1">
          {jobs.length} open position{jobs.length !== 1 ? 's' : ''} available
        </p>
      </div>

      {message && (
        <div
          className={`mb-6 p-4 rounded-lg flex items-start gap-3 ${
            message.type === 'success'
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
          }`}
        >
          {message.type === 'success' ? (
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          )}
          <p className={`text-sm ${message.type === 'success' ? 'text-green-800' : 'text-red-800'}`}>
            {message.text}
          </p>
        </div>
      )}

      {/* Indeed-style Split View */}
      <div className="flex gap-6 h-[calc(100vh-280px)]">
        {/* Left Panel - Job List */}
        <div className="w-2/5 overflow-y-auto pr-2 space-y-3">
          {jobs.map((job) => {
            const isSelected = selectedJob?.id === job.id;
            const hasApplied = appliedJobs.has(job.id);

            return (
              <div
                key={job.id}
                onClick={() => setSelectedJob(job)}
                className={`
                  card cursor-pointer transition-all duration-200 border-2
                  ${isSelected
                    ? 'border-primary-500 shadow-lg bg-primary-50'
                    : 'border-transparent hover:border-gray-200 hover:shadow-md'}
                `}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">{job.title}</h3>

                    <div className="flex items-center gap-3 mt-2 text-sm text-gray-500">
                      {job.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-4 h-4" />
                          {job.location}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {formatDate(job.created_at)}
                      </span>
                    </div>

                    <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                      {job.description}
                    </p>

                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {job.required_skills.slice(0, 3).map((skill) => (
                        <span
                          key={skill}
                          className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                        >
                          {skill}
                        </span>
                      ))}
                      {job.required_skills.length > 3 && (
                        <span className="px-2 py-0.5 text-gray-500 text-xs">
                          +{job.required_skills.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="ml-3 flex flex-col items-end">
                    {hasApplied && (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full font-medium">
                        Applied
                      </span>
                    )}
                    {isSelected && (
                      <ChevronRight className="w-5 h-5 text-primary-600 mt-2" />
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Panel - Job Details */}
        <div className="w-3/5 overflow-y-auto">
          {selectedJob ? (
            <div className="card h-full">
              {/* Header */}
              <div className="border-b border-gray-200 pb-6 mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">{selectedJob.title}</h2>

                <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600 mb-4">
                  {selectedJob.location && (
                    <span className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {selectedJob.location}
                    </span>
                  )}
                  {(selectedJob.min_years_experience || selectedJob.max_years_experience) && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {selectedJob.min_years_experience && selectedJob.max_years_experience
                        ? `${selectedJob.min_years_experience}-${selectedJob.max_years_experience} years`
                        : selectedJob.min_years_experience
                        ? `${selectedJob.min_years_experience}+ years`
                        : `Up to ${selectedJob.max_years_experience} years`}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    Posted {formatDate(selectedJob.created_at)}
                  </span>
                </div>

                {/* Apply Button */}
                <button
                  onClick={() => handleApply(selectedJob.id)}
                  disabled={applying === selectedJob.id || appliedJobs.has(selectedJob.id)}
                  className={`
                    px-8 py-3 rounded-lg font-medium transition-all text-lg
                    ${
                      appliedJobs.has(selectedJob.id)
                        ? 'bg-green-100 text-green-700 cursor-not-allowed'
                        : applying === selectedJob.id
                        ? 'bg-gray-300 text-gray-500 cursor-wait'
                        : 'btn-primary'
                    }
                  `}
                >
                  {appliedJobs.has(selectedJob.id) ? (
                    <span className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5" />
                      Applied Successfully
                    </span>
                  ) : applying === selectedJob.id ? (
                    <span className="flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Applying...
                    </span>
                  ) : (
                    'Apply Now'
                  )}
                </button>
              </div>

              {/* Description */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-900 mb-3">Job Description</h3>
                <div className="text-gray-700 whitespace-pre-line leading-relaxed">
                  {selectedJob.description}
                </div>
              </div>

              {/* Required Skills */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-900 mb-3">Required Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedJob.required_skills.map((skill) => (
                    <span
                      key={skill}
                      className="px-3 py-1.5 bg-primary-100 text-primary-700 rounded-full text-sm font-medium"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              {/* Must-Have Skills */}
              {selectedJob.must_have_skills && selectedJob.must_have_skills.length > 0 && (
                <div className="mb-6">
                  <h3 className="font-semibold text-gray-900 mb-3">Must-Have Skills</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedJob.must_have_skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-3 py-1.5 bg-red-100 text-red-700 rounded-full text-sm font-medium"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Experience Requirements */}
              {(selectedJob.min_years_experience || selectedJob.max_years_experience) && (
                <div className="mb-6">
                  <h3 className="font-semibold text-gray-900 mb-3">Experience Requirements</h3>
                  <p className="text-gray-700">
                    {selectedJob.min_years_experience && selectedJob.max_years_experience
                      ? `${selectedJob.min_years_experience} to ${selectedJob.max_years_experience} years of experience`
                      : selectedJob.min_years_experience
                      ? `Minimum ${selectedJob.min_years_experience} years of experience`
                      : `Maximum ${selectedJob.max_years_experience} years of experience`}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="card h-full flex items-center justify-center">
              <div className="text-center text-gray-500">
                <Briefcase className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                <p>Select a job to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
