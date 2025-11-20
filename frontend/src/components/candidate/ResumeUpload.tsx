import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, AlertCircle } from 'lucide-react';
import { candidatesApi } from '../../api/candidates';
import { useCandidateStore } from '../../store/candidateStore';

interface ResumeUploadProps {
  onSuccess: () => void;
}

export const ResumeUpload: React.FC<ResumeUploadProps> = ({ onSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { setTempId, setParsedData } = useCandidateStore();

  const onDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const response = await candidatesApi.uploadResume(file);
      setTempId(response.temp_id);
      setParsedData(response.parsed_data);
      onSuccess();
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Upload failed. Please try again.';
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="card max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-2 text-center text-gray-900">Upload Your Resume</h2>
      <p className="text-center text-gray-600 mb-6">
        We'll automatically extract your information to save you time
      </p>

      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300'}
          ${uploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary-400 hover:bg-gray-50'}
        `}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center gap-4">
          {uploading ? (
            <>
              <Upload className="w-12 h-12 text-primary-500 animate-bounce" />
              <p className="text-lg font-medium text-primary-700">Parsing your resume...</p>
              <p className="text-sm text-gray-500">This may take a few seconds</p>
            </>
          ) : (
            <>
              <FileText className="w-12 h-12 text-gray-400" />
              <p className="text-lg font-medium text-gray-700">
                {isDragActive
                  ? 'Drop your resume here'
                  : 'Drag & drop your resume, or click to browse'}
              </p>
              <p className="text-sm text-gray-500">Supports PDF, DOC, DOCX, TXT (Max 10MB)</p>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}
    </div>
  );
};
