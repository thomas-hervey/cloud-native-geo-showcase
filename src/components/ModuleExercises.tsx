'use client';

import React from 'react';
import dynamic from 'next/dynamic';

// Use dynamic import for client components
const ReadmeViewer = dynamic(() => import('./ReadmeViewer'), {
  ssr: false,
  loading: () => <div className="p-4 bg-gray-100 rounded-md">Loading README...</div>
});

interface ModuleExercisesProps {
  moduleName: string;
}

const ModuleExercises: React.FC<ModuleExercisesProps> = ({ moduleName }) => {
  return (
    <div className="mt-8">
      <ReadmeViewer moduleName={moduleName} />
    </div>
  );
};

export default ModuleExercises;
