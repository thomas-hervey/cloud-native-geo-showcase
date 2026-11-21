import fs from 'fs';
import path from 'path';
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { Metadata } from 'next';
import ModuleContent from '@/components/ModuleContent';
import SidebarAccordion from '@/components/SidebarAccordion';
import ModuleHeader from '@/components/ModuleHeader';
import ExerciseAccordion from '@/components/ExerciseAccordion';
import { getModule, getAdjacentModules, getCurriculum } from '@/lib/curriculum';
import { slugify } from '@/utils/slugify';
import { ChevronLeft, ChevronRight, Terminal, ExternalLink } from 'lucide-react';

const EXERCISES_REPO_URL = 'https://github.com/thomas-hervey/cloud-native-geo-exercises';

function parseH2Headings(content: string): { text: string; anchor: string }[] {
  return Array.from(content.matchAll(/^## (.+)$/gm)).map(m => {
    const raw = m[1].trim();
    // Strip inline markdown while preserving text content, to match h2 renderer's extractText behavior
    const plainText = raw
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')  // [text](url) → text
      .replace(/`([^`]+)`/g, '$1')               // `code` → code
      .replace(/\*\*([^*]+)\*\*/g, '$1')         // **bold** → bold
      .replace(/\*([^*]+)\*/g, '$1')             // *italic* → italic
      .replace(/[*_]/g, '')                       // remaining markers
      .trim();
    return { text: plainText, anchor: slugify(plainText) };
  });
}

// Get exercise files from the filesystem
function getLocalExercises(slug: string) {
  const exercisesDir = path.join(process.cwd(), 'src/exercises');
  if (!fs.existsSync(exercisesDir)) return [];

  const fullPath = path.join(exercisesDir, slug);
  if (!fs.existsSync(fullPath)) return [];

  const files = fs.readdirSync(fullPath);

  return files
    .filter(f => f.endsWith('.py') || f.endsWith('.md'))
    .map(f => {
      const content = fs.readFileSync(path.join(fullPath, f), 'utf8');
      return {
        filename: f,
        content,
        language: f.endsWith('.py') ? 'python' : 'markdown'
      };
    });
}

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const curriculum = getCurriculum();
  const mod = curriculum.modules[slug];

  return {
    title: mod ? `${mod.title} | Cloud-Native Geospatial Tutorial` : 'Module Not Found',
  };
}

export default async function ModulePage({ params }: Props) {
  const { slug } = await params;
  const moduleData = getModule(slug);

  if (!moduleData) {
    return notFound();
  }

  const curriculum = getCurriculum();
  const localExercises = getLocalExercises(slug);
  const { prev, next } = getAdjacentModules(slug);
  const headings = parseH2Headings(moduleData.content);

  return (
    <div className="flex flex-col xl:flex-row gap-8 max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-12 py-10">
      {/* Sidebar Navigation */}
      <aside className="xl:w-80 shrink-0">
        <SidebarAccordion curriculum={curriculum} currentSlug={slug} headings={headings} />
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0">
        {moduleData.metadata.reviewNeeded && (
          <div className="mb-6 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
            <span className="mt-0.5 shrink-0 text-amber-500">⚠</span>
            <div>
              <span className="font-semibold">Content needs review. </span>
              {moduleData.metadata.reviewNote
                ? moduleData.metadata.reviewNote
                : 'This module contains specific claims, benchmarks, or model descriptions that have not been independently verified. Citations are needed before this content should be relied upon.'}
            </div>
          </div>
        )}
        <div className="bg-white rounded-3xl border border-gray-100 shadow-2xl p-8 md:p-12 transition-all hover:shadow-3xl">
          <ModuleHeader metadata={moduleData.metadata} />
          
          <article className="prose prose-slate prose-lg max-w-none 
            prose-headings:font-black prose-headings:tracking-tight prose-headings:text-gray-900
            prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline
            prose-img:rounded-2xl prose-img:border prose-img:border-gray-100 prose-img:shadow-lg
            prose-code:text-blue-600 prose-code:bg-blue-50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded-md prose-code:before:content-none prose-code:after:content-none
            prose-strong:text-gray-900 prose-blockquote:border-l-4 prose-blockquote:border-blue-500 prose-blockquote:bg-blue-50 prose-blockquote:py-1 prose-blockquote:rounded-r-lg
          ">
            <ModuleContent content={moduleData.content} />
          </article>

          {/* Local Exercise Code Viewer */}
          {localExercises.length > 0 && (
            <div className="mt-20 border-t border-gray-100 pt-16">
              <div className="flex items-center gap-3 mb-8">
                <div className="bg-indigo-600 text-white p-3 rounded-2xl shadow-lg ring-4 ring-indigo-50">
                  <Terminal className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-3xl font-black text-gray-900 tracking-tight">Practical Implementation</h2>
                  <p className="text-gray-500 font-medium">Source files from <code>src/exercises/{slug}/</code></p>
                  {moduleData.metadata.exerciseFolder && (
                    <a
                      href={`${EXERCISES_REPO_URL}/tree/main/${moduleData.metadata.exerciseFolder}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 mt-1 text-sm font-medium text-blue-600 hover:underline"
                    >
                      Download exercise files from GitHub
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
              </div>

              <ExerciseAccordion files={localExercises} />
            </div>
          )}

          {/* Navigation Footer */}
          <nav className="mt-20 pt-10 border-t border-gray-100 grid grid-cols-1 sm:grid-cols-2 gap-6">
            {prev ? (
              <Link
                href={`/cng-modules/${prev.slug}`}
                className="group flex flex-col p-6 rounded-3xl border border-gray-100 bg-gray-50 hover:bg-white hover:border-blue-200 hover:shadow-xl transition-all"
              >
                <div className="flex items-center gap-2 text-blue-600 font-bold text-xs uppercase tracking-widest mb-2">
                  <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                  Previous Module
                </div>
                <span className="text-gray-900 font-black text-lg group-hover:text-blue-700 transition-colors leading-tight">
                  {prev.title}
                </span>
              </Link>
            ) : (
              <div />
            )}

            {next && (
              <Link
                href={`/cng-modules/${next.slug}`}
                className="group flex flex-col p-6 rounded-3xl border border-gray-100 bg-gray-50 hover:bg-white hover:border-blue-200 hover:shadow-xl transition-all text-right"
              >
                <div className="flex items-center gap-2 text-blue-600 font-bold text-xs uppercase tracking-widest mb-2 justify-end">
                  Next Module
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
                <span className="text-gray-900 font-black text-lg group-hover:text-blue-700 transition-colors leading-tight">
                  {next.title}
                </span>
              </Link>
            )}
          </nav>
        </div>
      </main>
    </div>
  );
}

// Generate static paths for all modules
export async function generateStaticParams() {
  const curriculum = getCurriculum();
  return Object.keys(curriculum.modules).map(slug => ({
    slug,
  }));
}
