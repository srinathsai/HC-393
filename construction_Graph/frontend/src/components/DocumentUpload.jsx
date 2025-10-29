import { useState } from 'react';

export default function DocumentUpload({ onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [progress, setProgress] = useState(null);
  const [processingDetails, setProcessingDetails] = useState([]);

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    setFiles(selectedFiles);
    setUploadStatus('');
    setProgress(null);
    setProcessingDetails([]);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setUploadStatus('Please select at least one file');
      return;
    }

    if (files.length > 20) {
      setUploadStatus('Maximum 20 files allowed per upload');
      return;
    }

    setUploading(true);
    setUploadStatus('📤 Uploading files...');
    setProcessingDetails([]);

    try {
      const formData = new FormData();
      
      if (files.length === 1) {
        formData.append('file', files[0]);
        
        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        setUploadStatus(`✅ Upload complete! Processing document...`);
        
        setProcessingDetails([{
          filename: files[0].name,
          status: 'processing',
          jobId: data.job_id
        }]);
        
        if (data.job_id) {
          pollJobCompletion(data.job_id, files[0].name);
        }
      } else {
        files.forEach((file) => {
          formData.append('files', file);
        });

        const response = await fetch('http://localhost:8000/upload-multiple', {
          method: 'POST',
          body: formData
        });
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        
        setProgress({
          total: data.total_files,
          successful: data.successful,
          failed: data.failed,
          completed: 0
        });
        
        setUploadStatus(
          `✅ Uploaded ${data.successful}/${data.total_files} files. Processing...`
        );
        
        const details = data.details.map(detail => ({
          filename: detail.filename,
          status: detail.status === 'queued' ? 'processing' : 'failed',
          jobId: detail.job_id,
          error: detail.error
        }));
        setProcessingDetails(details);
        
        if (data.job_ids && data.job_ids.length > 0) {
          pollJobsCompletion(data.job_ids, data.details);
        }
      }
      
      setFiles([]);
      
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus(`❌ Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const pollJobCompletion = async (jobId, filename) => {
    const maxAttempts = 60;
    let attempts = 0;

    const checkStatus = async () => {
      try {
        const response = await fetch(`http://localhost:8000/job/${jobId}`);
        const data = await response.json();

        if (data.status === 'finished') {
          setProcessingDetails([{
            filename: filename,
            status: 'complete',
            jobId: jobId
          }]);
          setUploadStatus('🎉 Document processed successfully!');
          
          if (onUploadSuccess) {
            setTimeout(() => onUploadSuccess(), 500);
          }
        } else if (data.status === 'failed') {
          setProcessingDetails([{
            filename: filename,
            status: 'failed',
            jobId: jobId,
            error: data.error
          }]);
          setUploadStatus(`❌ Processing failed: ${data.error || 'Unknown error'}`);
        } else if (attempts < maxAttempts) {
          attempts++;
          const elapsed = Math.floor(attempts * 2 / 60);
          setUploadStatus(`⏳ Processing document... (${elapsed}m ${(attempts * 2) % 60}s)`);
          setTimeout(checkStatus, 2000);
        } else {
          setUploadStatus('⚠️ Processing is taking longer than expected...');
        }
      } catch (error) {
        console.error('Job status check error:', error);
      }
    };

    setTimeout(checkStatus, 1000);
  };

  const pollJobsCompletion = async (jobIds, fileDetails) => {
    const maxAttempts = 60;
    let attempts = 0;
    const total = jobIds.length;

    const checkJobs = async () => {
      try {
        const statuses = await Promise.all(
          jobIds.map(async (jobId) => {
            try {
              const response = await fetch(`http://localhost:8000/job/${jobId}`);
              return await response.json();
            } catch {
              return { status: 'unknown' };
            }
          })
        );

        const updatedDetails = fileDetails.map((detail, index) => {
          const jobStatus = statuses[index];
          return {
            filename: detail.filename,
            status: jobStatus.status === 'finished' ? 'complete' : 
                   jobStatus.status === 'failed' ? 'failed' : 'processing',
            jobId: detail.job_id,
            error: jobStatus.status === 'failed' ? jobStatus.error : null
          };
        });
        setProcessingDetails(updatedDetails);

        const completed = statuses.filter(s => s.status === 'finished').length;
        const failed = statuses.filter(s => s.status === 'failed').length;
        const processing = total - completed - failed;

        setProgress(prev => ({
          ...prev,
          completed: completed,
          failed: failed
        }));

        if (processing > 0) {
          attempts++;
          const elapsed = Math.floor(attempts * 3 / 60);
          const percent = Math.round((completed / total) * 100);
          setUploadStatus(
            `⏳ Processing: ${completed}/${total} complete (${percent}%) - ${elapsed}m elapsed${
              failed > 0 ? ` - ${failed} failed` : ''
            }`
          );
          setTimeout(checkJobs, 3000);
        } else {
          if (failed === 0) {
            setUploadStatus(`🎉 All ${total} documents processed successfully!`);
          } else {
            setUploadStatus(
              `✅ Processing complete: ${completed} successful, ${failed} failed`
            );
          }
          
          if (onUploadSuccess) {
            setTimeout(() => onUploadSuccess(), 500);
          }
        }
      } catch (error) {
        console.error('Job polling error:', error);
      }
    };

    setTimeout(checkJobs, 1000);
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  return (
    <div style={{
      background: '#1e293b',
      borderRadius: '0.75rem',
      padding: '1.5rem',
      boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
    }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem' }}>
        📤 Upload Documents
      </h2>
      
      <input
        type="file"
        accept=".pdf"
        multiple
        onChange={handleFileChange}
        style={{
          width: '100%',
          padding: '0.75rem',
          background: '#334155',
          border: '2px dashed #64748b',
          borderRadius: '0.5rem',
          color: '#e2e8f0',
          cursor: 'pointer'
        }}
      />
      
      {files.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <p style={{ fontSize: '0.875rem', marginBottom: '0.5rem', opacity: 0.8 }}>
            Selected {files.length} file(s):
          </p>
          <div style={{ maxHeight: '150px', overflowY: 'auto' }}>
            {files.map((file, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.5rem',
                  background: '#334155',
                  borderRadius: '0.25rem',
                  marginBottom: '0.5rem',
                  fontSize: '0.75rem'
                }}
              >
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {file.name}
                </span>
                <button
                  onClick={() => removeFile(index)}
                  style={{
                    marginLeft: '0.5rem',
                    padding: '0.25rem 0.5rem',
                    background: '#ef4444',
                    border: 'none',
                    borderRadius: '0.25rem',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '0.75rem'
                  }}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={files.length === 0 || uploading}
        style={{
          marginTop: '1rem',
          width: '100%',
          padding: '0.75rem',
          background: uploading ? '#475569' : '#6366f1',
          color: 'white',
          border: 'none',
          borderRadius: '0.5rem',
          fontWeight: 'bold',
          cursor: uploading || files.length === 0 ? 'not-allowed' : 'pointer',
          opacity: uploading || files.length === 0 ? 0.6 : 1
        }}
      >
        {uploading ? 'Uploading...' : `Upload ${files.length} File${files.length !== 1 ? 's' : ''}`}
      </button>

      {progress && (
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem',
          background: '#334155',
          borderRadius: '0.5rem',
          fontSize: '0.875rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span>Total: {progress.total}</span>
            <span style={{ color: '#10b981' }}>Complete: {progress.completed || 0}</span>
            {progress.failed > 0 && (
              <span style={{ color: '#ef4444' }}>Failed: {progress.failed}</span>
            )}
          </div>
          <div style={{
            width: '100%',
            height: '8px',
            background: '#1e293b',
            borderRadius: '4px',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${((progress.completed || 0) / progress.total) * 100}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #10b981, #059669)',
              transition: 'width 0.3s ease'
            }} />
          </div>
        </div>
      )}

      {processingDetails.length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <p style={{ fontSize: '0.875rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
            File Status:
          </p>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            {processingDetails.map((detail, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '0.5rem',
                  background: '#334155',
                  borderRadius: '0.25rem',
                  marginBottom: '0.5rem',
                  fontSize: '0.75rem'
                }}
              >
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {detail.filename}
                </span>
                <span style={{
                  padding: '0.25rem 0.5rem',
                  borderRadius: '0.25rem',
                  fontSize: '0.7rem',
                  fontWeight: 'bold',
                  background: 
                    detail.status === 'complete' ? '#065f46' :
                    detail.status === 'failed' ? '#991b1b' :
                    detail.status === 'processing' ? '#1e40af' : '#475569',
                  color: 'white'
                }}>
                  {detail.status === 'complete' ? '✓ Complete' :
                   detail.status === 'failed' ? '✗ Failed' :
                   detail.status === 'processing' ? '⏳ Processing' : 'Queued'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {uploadStatus && (
        <div style={{
          marginTop: '1rem',
          padding: '0.75rem',
          background: 
            uploadStatus.includes('🎉') ? '#065f46' :
            uploadStatus.includes('❌') ? '#991b1b' :
            uploadStatus.includes('⏳') ? '#1e40af' :
            uploadStatus.includes('✅') ? '#065f46' : '#334155',
          borderRadius: '0.5rem',
          fontSize: '0.875rem',
          fontWeight: uploadStatus.includes('🎉') ? 'bold' : 'normal'
        }}>
          {uploadStatus}
        </div>
      )}
    </div>
  );
}
