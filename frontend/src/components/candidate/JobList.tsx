import React, { useEffect, useState } from 'react';
import { candidatesApi } from '../../api/candidates';
import { Briefcase, MapPin, DollarSign, CheckCircle, AlertCircle } from 'lucide-react';
import { Job } from '../../types';
import { Loading } from '../shared/Loading';

interface JobListProps {
  candidateId: string;
}

export const JobList: React.FC<JobListProps> = ({ candidateId }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
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
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Available Jobs</h2>
        <p className="text-gray-600 mt-1">
          Browse and apply to open positions that match your skills
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
          <p
            className={`text-sm ${
              message.type === 'success' ? 'text-green-800' : 'text-red-800'
            }`}
          >
            {message.text}
          </p>
        </div>
      )}

      <div className="space-y-4">
        {jobs.map((job) => {
          const hasApplied = appliedJobs.has(job.id);
          const isApplying = applying === job.id;

          return (
            <div key={job.id} className="card hover:shadow-lg transition-shadow">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">{job.title}</h3>
                  {job.company_name && (
                    <p className="text-gray-600 font-medium mb-2">{job.company_name}</p>
                  )}

                  <div className="flex flex-wrap gap-4 text-sm text-gray-500 mb-3">
                    {job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-4 h-4" />
                        {job.location}
                      </span>
                    )}
                    {job.salary_min && job.salary_max && (
                      <span className="flex items-center gap-1">
                        <DollarSign className="w-4 h-4" />
                        ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()}
                      </span>
                    )}
                  </div>

                  <p className="text-gray-700 mb-3 line-clamp-2">{job.description}</p>

                  <div className="flex flex-wrap gap-2">
                    {job.required_skills.map((skill) => (
                      <span
                        key={skill}
                        className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full text-sm font-medium"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="ml-4">
                  <button
                    onClick={() => handleApply(job.id)}
                    disabled={isApplying || hasApplied}
                    className={`
                      px-6 py-2 rounded-lg font-medium transition-all
                      ${
                        hasApplied
                          ? 'bg-green-100 text-green-700 cursor-not-allowed'
                          : isApplying
                          ? 'bg-gray-300 text-gray-500 cursor-wait'
                          : 'btn-primary'
                      }
                    `}
                  >
                    {hasApplied ? (
                      <span className="flex items-center gap-2">
                        <CheckCircle className="w-4 h-4" />
                        Applied
                      </span>
                    ) : isApplying ? (
                      'Applying...'
                    ) : (
                      'Apply Now'
                    )}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
