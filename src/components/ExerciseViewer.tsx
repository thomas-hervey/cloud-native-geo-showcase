'use client';

import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ExerciseViewerProps {
  exercises: {
    title: string;
    description: string;
    language: string;
    code: string;
    instructions?: string;
  }[];
}

const ExerciseViewer: React.FC<ExerciseViewerProps> = ({ exercises }) => {
  const [activeExercise, setActiveExercise] = useState(0);

  if (!exercises || exercises.length === 0) {
    return <div className="p-4 bg-yellow-50 text-yellow-800 rounded-md">No exercises available for this module.</div>;
  }

  const exercise = exercises[activeExercise];

  return (
    <div className="mt-8 border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-blue-600 text-white px-4 py-3">
        <h3 className="text-xl font-bold">Practical Exercises</h3>
      </div>
      
      {/* Exercise tabs */}
      <div className="flex border-b border-gray-200 bg-gray-50">
        {exercises.map((ex, index) => (
          <button
            key={index}
            className={`px-4 py-2 text-sm font-medium ${
              activeExercise === index
                ? 'bg-white border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600 hover:text-blue-500'
            }`}
            onClick={() => setActiveExercise(index)}
          >
            {ex.title}
          </button>
        ))}
      </div>
      
      {/* Exercise content */}
      <div className="p-4 bg-white">
        <div className="mb-4">
          <h4 className="text-lg font-semibold text-gray-800">{exercise.title}</h4>
          <p className="text-gray-600 mt-1">{exercise.description}</p>
        </div>
        
        {exercise.instructions && (
          <div className="mb-4 p-3 bg-blue-50 rounded-md text-sm">
            <h5 className="font-semibold text-blue-800 mb-1">Instructions:</h5>
            <p className="text-blue-700">{exercise.instructions}</p>
          </div>
        )}
        
        <div className="mt-4">
          <div className="flex justify-between items-center mb-2">
            <h5 className="font-semibold text-gray-700">Code:</h5>
            <button
              className="text-sm text-blue-600 hover:text-blue-800"
              onClick={() => {
                navigator.clipboard.writeText(exercise.code);
                alert('Code copied to clipboard!');
              }}
            >
              Copy to clipboard
            </button>
          </div>
          <SyntaxHighlighter 
            language={exercise.language} 
            style={tomorrow}
            customStyle={{ borderRadius: '0.375rem' }}
            showLineNumbers={true}
          >
            {exercise.code}
          </SyntaxHighlighter>
        </div>
      </div>
    </div>
  );
};

export default ExerciseViewer;
