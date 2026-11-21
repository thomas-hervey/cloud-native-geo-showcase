'use client';

import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ReadmeViewerProps {
  moduleName: string;
}

const ReadmeViewer: React.FC<ReadmeViewerProps> = ({ moduleName }) => {
  const [readmeContent, setReadmeContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReadme = async () => {
      try {
        setIsLoading(true);
        // Attempt to fetch the README.md file for the specified module
        const response = await fetch(`/api/readme?module=${moduleName}`);
        
        if (!response.ok) {
          throw new Error(`Failed to load README for ${moduleName}`);
        }
        
        const content = await response.text();
        setReadmeContent(content);
        setError(null);
      } catch (err) {
        console.error('Error loading README:', err);
        setError(`Could not load README for ${moduleName}. The exercises might not have a README file.`);
      } finally {
        setIsLoading(false);
      }
    };

    if (moduleName) {
      fetchReadme();
    }
  }, [moduleName]);

  if (isLoading) {
    return (
      <div className="p-4 bg-gray-100 rounded-md animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-yellow-50 text-yellow-800 rounded-md">
        {error}
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-blue-600 text-white px-4 py-3">
        <h3 className="text-xl font-bold">Exercise Instructions</h3>
      </div>
      <div className="p-4 bg-white markdown-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {readmeContent}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default ReadmeViewer;
