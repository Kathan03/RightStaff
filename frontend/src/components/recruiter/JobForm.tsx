import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Briefcase, AlertCircle } from 'lucide-react';
import { jobsApi } from '../../api/jobs';
import { CreateJobRequest } from '../../types';

const schema = z.object({
  title: z.string().min(5, 'Title must be at least 5 characters'),
  description: z.string().min(50, 'Description must be at least 50 characters'),
  required_skills_str: z.string().min(1, 'At least one skill required'),
  must_have_skills_str: z.string().optional(),
  location: z.string().optional(),
  min_years_experience: z.number().min(0).optional(),
  max_years_experience: z.number().min(0).optional(),
});

type FormData = z.infer<typeof schema>;

interface JobFormProps {
  onSuccess: (jobId: string) => void;
}

export const JobForm: React.FC<JobFormProps> = ({ onSuccess }) => {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    setError(null);

    try {
      // Convert skills strings to arrays
      const required_skills = data.required_skills_str
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const must_have_skills = data.must_have_skills_str
        ? data.must_have_skills_str
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean)
        : [];

      const request: CreateJobRequest = {
        title: data.title,
        description: data.description,
        required_skills,
        must_have_skills,
        location: data.location || undefined,
        min_years_experience: data.min_years_experience,
        max_years_experience: data.max_years_experience,
      };

      const response = await jobsApi.createJob(request);
      reset();
      onSuccess(response.job_id);
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Job creation failed. Please try again.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Briefcase className="w-8 h-8 text-primary-600" />
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Create New Job</h2>
          <p className="text-gray-600">Post a new position to find the right candidates</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Job Title <span className="text-red-500">*</span>
          </label>
          <input
            {...register('title')}
            className="input-field"
            placeholder="Senior Python Developer"
          />
          {errors.title && (
            <p className="text-red-600 text-sm mt-1">{errors.title.message}</p>
          )}
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Job Description <span className="text-red-500">*</span>
          </label>
          <textarea
            {...register('description')}
            rows={6}
            className="input-field"
            placeholder="We're looking for an experienced developer to join our team..."
          />
          {errors.description && (
            <p className="text-red-600 text-sm mt-1">{errors.description.message}</p>
          )}
        </div>

        {/* Required Skills */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Required Skills (comma-separated) <span className="text-red-500">*</span>
          </label>
          <input
            {...register('required_skills_str')}
            className="input-field"
            placeholder="Python, Django, PostgreSQL, AWS"
          />
          <p className="text-xs text-gray-500 mt-1">
            List all skills required for this position
          </p>
          {errors.required_skills_str && (
            <p className="text-red-600 text-sm mt-1">{errors.required_skills_str.message}</p>
          )}
        </div>

        {/* Must-Have Skills */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Must-Have Skills (comma-separated)
          </label>
          <input
            {...register('must_have_skills_str')}
            className="input-field"
            placeholder="Python, PostgreSQL"
          />
          <p className="text-xs text-gray-500 mt-1">
            Critical skills that candidates must have (used for hard filtering)
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Min Years Experience */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Min Years Experience
            </label>
            <input
              {...register('min_years_experience', { valueAsNumber: true })}
              type="number"
              min="0"
              className="input-field"
              placeholder="3"
            />
          </div>

          {/* Max Years Experience */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Years Experience
            </label>
            <input
              {...register('max_years_experience', { valueAsNumber: true })}
              type="number"
              min="0"
              className="input-field"
              placeholder="10"
            />
          </div>
        </div>

        {/* Location */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Location</label>
          <input
            {...register('location')}
            className="input-field"
            placeholder="San Francisco, CA"
          />
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}

        <button type="submit" disabled={submitting} className="btn-primary w-full">
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Creating Job...
            </span>
          ) : (
            'Create Job'
          )}
        </button>
      </form>
    </div>
  );
};
