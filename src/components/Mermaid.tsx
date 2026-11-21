'use client';

import React, { useEffect, useState, useId } from 'react';

interface MermaidProps {
  content: string;
}

// Ensure mermaid is initialized only once
let isInitialized = false;

const Mermaid: React.FC<MermaidProps> = ({ content }) => {
  const uniqueId = useId();
  // Mermaid IDs must start with a letter and not contain colons
  const chartId = `mermaid-${uniqueId.replace(/:/g, '')}`;
  
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function renderDiagram() {
      setIsInitializing(true);
      setError(null);

      try {
        console.log(`[Mermaid] Starting render for ${chartId}`);
        const mermaid = (await import('mermaid')).default;
        
        if (!isInitialized) {
          mermaid.initialize({
            startOnLoad: false,
            theme: 'base',
            securityLevel: 'loose',
            themeVariables: {
              fontFamily: 'ui-sans-serif, system-ui, sans-serif',
              primaryColor: '#eff6ff',
              primaryTextColor: '#1e3a8a',
              primaryBorderColor: '#bfdbfe',
              lineColor: '#3b82f6',
              secondaryColor: '#f8fafc',
              tertiaryColor: '#ffffff',
              noteBkgColor: '#fffbeb',
              noteTextColor: '#92400e',
            }
          });
          isInitialized = true;
        }

        // Validate content before rendering
        if (!content || content.trim() === '') {
          throw new Error('Empty diagram content');
        }

        const { svg: renderedSvg } = await mermaid.render(chartId, content);
        
        if (isMounted) {
          console.log(`[Mermaid] Successfully rendered ${chartId}`);
          setSvg(renderedSvg);
        }
      } catch (err) {
        console.error(`[Mermaid] Render error for ${chartId}:`, err);
        if (isMounted) {
          setError(err instanceof Error ? err.message : String(err));
        }
      } finally {
        if (isMounted) {
          setIsInitializing(false);
        }
      }
    }

    renderDiagram();

    return () => {
      isMounted = false;
    };
  }, [content, chartId]);

  if (error) {
    return (
      <div className="my-6 p-4 rounded-xl border border-red-100 bg-red-50 text-red-900 text-sm overflow-auto italic">
        <p className="font-bold mb-2">Diagram Render Error:</p>
        <pre className="text-xs bg-white/50 p-2 rounded border border-red-200">{content}</pre>
        <p className="mt-2 text-[10px] opacity-70 italic">{error}</p>
      </div>
    );
  }

  if (isInitializing) {
    return (
      <div className="my-6 h-32 flex items-center justify-center bg-gray-50 rounded-2xl border border-gray-100 animate-pulse">
        <div className="flex flex-col items-center gap-2 text-gray-400">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs font-medium uppercase tracking-widest">Rendering Diagram...</span>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="mermaid-container my-8 flex justify-center bg-white p-8 rounded-3xl border border-gray-100 shadow-sm overflow-x-auto transition-all hover:shadow-md"
      dangerouslySetInnerHTML={{ __html: svg || '' }} 
    />
  );
};

export default Mermaid;
