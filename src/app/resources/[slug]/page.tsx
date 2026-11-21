import fs from 'fs';
import path from 'path';
import { notFound } from 'next/navigation';
import { Metadata } from 'next';
import Link from 'next/link';
import matter from 'gray-matter';
import ModuleContent from '@/components/ModuleContent';

// Get specific resource content
function getResourceContent(slug: string) {
    const resourcesDir = path.join(process.cwd(), 'src/content/resources');
    const filePath = path.join(resourcesDir, `${slug}.md`);

    if (!fs.existsSync(filePath)) {
        return null;
    }

    const fileContents = fs.readFileSync(filePath, 'utf8');
    const { data, content } = matter(fileContents);

    return {
        slug,
        title: data.title || slug,
        date: data.date || '',
        source: data.source || '',
        content
    };
}

type Props = {
    params: Promise<{ slug: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const { slug } = await params;
    const resourceData = getResourceContent(slug);

    return {
        title: resourceData ? `${resourceData.title} | Resources` : 'Resource Not Found',
    };
}

export default async function ResourcePage({ params }: Props) {
    const { slug } = await params;
    const resourceData = getResourceContent(slug);

    if (!resourceData) {
        return notFound();
    }

    return (
        <div className="max-w-4xl mx-auto py-8 px-4">
            <div className="mb-6">
                <Link
                    href="/resources"
                    className="inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors mb-4"
                >
                    <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Back to Resources
                </Link>
                <h1 className="text-3xl font-bold text-gray-900 mb-2">{resourceData.title}</h1>
                <div className="flex gap-4 text-sm text-gray-600">
                    {resourceData.date && <span>📅 Date: {resourceData.date}</span>}
                    {resourceData.source && <span>🤖 Source: {resourceData.source}</span>}
                </div>
            </div>

            <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-8">
                <article className="prose prose-blue max-w-none">
                    <ModuleContent content={resourceData.content} />
                </article>
            </div>
        </div>
    );
}

export async function generateStaticParams() {
    const resourcesDir = path.join(process.cwd(), 'src/content/resources');

    if (!fs.existsSync(resourcesDir)) {
        return [];
    }

    const filenames = fs.readdirSync(resourcesDir);
    return filenames
        .filter(filename => filename.endsWith('.md'))
        .map(filename => ({
            slug: filename.replace(/\.md$/, ''),
        }));
}
