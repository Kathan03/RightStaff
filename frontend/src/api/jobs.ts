import { apiClient } from './client';
import {
  CreateJobRequest,
  CreateJobResponse,
  Job,
  RankingResponse,
  ApplicantsResponse
} from '../types';

export const jobsApi = {
  // Create job
  createJob: async (request: CreateJobRequest): Promise<CreateJobResponse> => {
    const { data } = await apiClient.post('/api/v1/jobs/', request);
    return data;
  },

  // Get all jobs
  getAllJobs: async (): Promise<Job[]> => {
    try {
      const { data } = await apiClient.get('/api/v1/jobs/');
      return data;
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      return [];
    }
  },

  // Get job by ID
  getJob: async (jobId: string): Promise<Job> => {
    const { data } = await apiClient.get(`/api/v1/jobs/${jobId}`);
    return data;
  },

  // Rank candidates for job - CORRECTED TO USE rank_full
  rankCandidates: async (jobId: string, useCache = true): Promise<RankingResponse> => {
    const { data } = await apiClient.post(`/api/v1/jobs/${jobId}/rank_full`, {
      use_cache: useCache,
    });
    return data;
  },

  // Get all applicants for a job
  getApplicants: async (jobId: string): Promise<ApplicantsResponse> => {
    const { data } = await apiClient.get(`/api/v1/jobs/${jobId}/applicants`);
    return data;
  },
};
