'use client';

import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import dynamic from 'next/dynamic';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import FileTree from './FileTree';
import { extractExercisesFromMarkdown, Exercise } from '../utils/exerciseParser';
import { slugify } from '@/utils/slugify';

function extractText(node: React.ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (Array.isArray(node)) return node.map(extractText).join('');
  if (React.isValidElement(node)) {
    return extractText((node.props as { children?: React.ReactNode }).children);
  }
  return '';
}

interface ModuleContentProps {
  content: string;
}

const Mermaid = dynamic(() => import('./Mermaid'), {
  ssr: false,
  loading: () => <div className="p-4 bg-gray-100 rounded-2xl animate-pulse h-32 flex items-center justify-center text-xs uppercase tracking-widest text-gray-400 font-bold">Loading Diagram...</div>
});

const ExerciseViewer = dynamic(() => import('./ExerciseViewer'), {
  ssr: false,
  loading: () => <div className="p-4 bg-gray-100 rounded-md">Loading exercises...</div>
});

const ModuleContent: React.FC<ModuleContentProps> = ({ content }) => {
  const [exercises, setExercises] = useState<Exercise[]>([]);

  useEffect(() => {
    // Extract exercises from the markdown content
    const extractedExercises = extractExercisesFromMarkdown(content);
    setExercises(extractedExercises);
  }, [content]);

  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h2(props) {
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { children, node: _node, ...rest } = props;
            const text = extractText(children as React.ReactNode);
            return <h2 id={slugify(text)} {...rest}>{children}</h2>;
          },
          code(props) {
            const { children, className, ...rest } = props
            const match = /language-(\w+)/.exec(className || '')
            const language = match ? match[1] : ''

            if (language === 'filetree') {
              return <FileTree content={String(children).replace(/\n$/, '')} />
            }

            if (language === 'mermaid') {
              return <Mermaid content={String(children).replace(/\n$/, '')} />
            }

            if (match) {
              return (
                <div className="my-4 rounded-lg overflow-hidden border border-gray-700">
                  <SyntaxHighlighter
                    behavior="pre"
                    style={vscDarkPlus}
                    language={language}
                    PreTag="div"
                    customStyle={{
                      margin: 0,
                      padding: '1.5rem',
                      fontSize: '0.9rem',
                      lineHeight: '1.5',
                    }}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                </div>
              )
            }

            return (
              <code {...rest} className="px-1.5 py-0.5 rounded bg-gray-100 text-blue-600 font-mono text-sm border border-gray-200">
                {children}
              </code>
            )
          }
        }}
      >
        {content}
      </ReactMarkdown>

      {exercises.length > 0 && (
        <ExerciseViewer exercises={exercises} />
      )}
    </div>
  );
};

export default ModuleContent;
