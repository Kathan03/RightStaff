import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AlertCircle, CheckCircle } from 'lucide-react';
import { candidatesApi } from '../../api/candidates';
import { useCandidateStore } from '../../store/candidateStore';
import { CreateCandidateRequest } from '../../types';

const schema = z.object({
  full_name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address').or(z.string().length(0)).optional(),
  phone: z.string().optional(),
  location: z.string().optional(),
  years_experience: z.number().min(0).max(50).optional(),
  professional_summary: z.string().min(20, 'Summary must be at least 20 characters').optional(),
  skills_str: z.string().min(1, 'At least one skill required'),
});

type FormData = z.infer<typeof schema>;

interface CandidateFormProps {
  onSuccess: () => void;
}

export const CandidateForm: React.FC<CandidateFormProps> = ({ onSuccess }) => {
  const { tempId, parsedData, setCandidateId } = useCandidateStore();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  // Pre-fill form with parsed data
  useEffect(() => {
    if (parsedData) {
      setValue('full_name', parsedData.full_name || '');
      setValue('email', parsedData.email || '');
      setValue('phone', parsedData.phone || '');
      setValue('location', parsedData.location || '');
      setValue('years_experience', parsedData.years_experience || undefined);
      setValue('professional_summary', parsedData.professional_summary || '');
      setValue('skills_str', parsedData.skills?.join(', ') || '');
    }
  }, [parsedData, setValue]);

  const onSubmit = async (data: FormData) => {
    if (!tempId) {
      setError('No temp_id found. Please upload resume first.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const request: CreateCandidateRequest = {
        temp_id: tempId,
        full_name: data.full_name,
        email: data.email || undefined,
        phone: data.phone || undefined,
        location: data.location || undefined,
        years_experience: data.years_experience,
        professional_summary: data.professional_summary || undefined,
      };

      const response = await candidatesApi.createCandidate(request);
      setCandidateId(response.candidate_id);
      onSuccess();
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Submission failed. Please try again.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card max-w-3xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Complete Your Profile</h2>
        <p className="text-gray-600">Review and update your information</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Full Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Full Name <span className="text-red-500">*</span>
          </label>
          <input
            {...register('full_name')}
            className="input-field"
            placeholder="John Doe"
          />
          {errors.full_name && (
            <p className="text-red-600 text-sm mt-1">{errors.full_name.message}</p>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input
              {...register('email')}
              type="email"
              className="input-field"
              placeholder="john@example.com"
            />
            {errors.email && (
              <p className="text-red-600 text-sm mt-1">{errors.email.message}</p>
            )}
          </div>

          {/* Phone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Phone</label>
            <input
              {...register('phone')}
              className="input-field"
              placeholder="+1 (555) 123-4567"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Location */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Location</label>
            <input
              {...register('location')}
              className="input-field"
              placeholder="San Francisco, CA"
            />
          </div>

          {/* Years Experience */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Years of Experience
            </label>
            <input
              {...register('years_experience', { valueAsNumber: true })}
              type="number"
              min="0"
              max="50"
              className="input-field"
              placeholder="5"
            />
          </div>
        </div>

        {/* Skills */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Skills (comma-separated) <span className="text-red-500">*</span>
          </label>
          <input
            {...register('skills_str')}
            className="input-field"
            placeholder="Python, React, PostgreSQL"
          />
          <p className="text-xs text-gray-500 mt-1">
            Separate skills with commas. Example: JavaScript, Node.js, MongoDB
          </p>
          {errors.skills_str && (
            <p className="text-red-600 text-sm mt-1">{errors.skills_str.message}</p>
          )}
        </div>

        {/* Professional Summary */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Professional Summary
          </label>
          <textarea
            {...register('professional_summary')}
            rows={5}
            className="input-field"
            placeholder="Brief summary of your experience and expertise..."
          />
          {errors.professional_summary && (
            <p className="text-red-600 text-sm mt-1">{errors.professional_summary.message}</p>
          )}
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
              Creating Profile...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <CheckCircle className="w-5 h-5" />
              Create Profile & Continue
            </span>
          )}
        </button>
      </form>
    </div>
  );
};
