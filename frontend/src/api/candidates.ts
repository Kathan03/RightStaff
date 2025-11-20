import { apiClient } from './client';
import {
  UploadResumeResponse,
  CreateCandidateRequest,
  CreateCandidateResponse,
  Job,
  ApplyToJobResponse
} from '../types';

export const candidatesApi = {
  // Upload resume (anonymous) - CORRECTED ENDPOINT
  uploadResume: async (file: File): Promise<UploadResumeResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await apiClient.post('/api/v1/candidates/upload-resume', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // Create full candidate profile - CORRECTED ENDPOINT
  createCandidate: async (request: CreateCandidateRequest): Promise<CreateCandidateResponse> => {
    const { data } = await apiClient.post('/api/v1/candidates/', request);
    return data;
  },

  // Get all jobs - Note: Backend doesn't have this endpoint yet
  // Will return empty array for now
  getJobs: async (): Promise<Job[]> => {
    try {
      const { data } = await apiClient.get('/api/v1/jobs');
      return data;
    } catch (error) {
      console.warn('GET /api/v1/jobs not implemented in backend, returning empty array');
      return [];
    }
  },

  // Apply to job - CORRECTED TO MATCH BACKEND
  applyToJob: async (jobId: string, candidateId: string): Promise<ApplyToJobResponse> => {
    const { data } = await apiClient.post(`/api/v1/jobs/${jobId}/apply`, {
      candidate_id: candidateId,
    });
    return data;
  },
};
