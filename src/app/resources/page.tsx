import fs from 'fs';
import path from 'path';
import { Metadata } from 'next';
import Link from 'next/link';
import matter from 'gray-matter';

export const metadata: Metadata = {
    title: 'Resources | Cloud-Native Geospatial Tutorial',
    description: 'Explore extra resources, reports, and generated artifacts regarding the geospatial industry.',
};

function getResources() {
    const resourcesDir = path.join(process.cwd(), 'src/content/resources');

    // Create dir if it doesn't exist to prevent errors
    if (!fs.existsSync(resourcesDir)) {
        return [];
    }

    const filenames = fs.readdirSync(resourcesDir);

    return filenames
        .filter(filename => filename.endsWith('.md'))
        .map(filename => {
            const filePath = path.join(resourcesDir, filename);
            const fileContents = fs.readFileSync(filePath, 'utf8');
            const { data } = matter(fileContents);

            return {
                slug: filename.replace(/\.md$/, ''),
                title: data.title || filename,
                date: data.date || '',
                source: data.source || 'Unknown',
                status: data.status || 'todo',
            };
        })
        .sort((a, b) => {
            // Sort by date descending
            return new Date(b.date).getTime() - new Date(a.date).getTime();
        });
}

function getStatusBadgeClasses(status: string) {
    switch (status.toLowerCase()) {
        case 'accomplished':
            return 'bg-green-100 text-green-800 border-green-200';
        case 'in progress':
            return 'bg-blue-100 text-blue-800 border-blue-200';
        case 'todo':
        default:
            return 'bg-gray-100 text-gray-800 border-gray-200';
    }
}

export default function ResourcesPage() {
    const resources = getResources();


    return (
        <div className="max-w-5xl mx-auto py-8 px-4">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-4">Resources & Reports</h1>
                <p className="text-lg text-gray-700">
                    A collection of industry reports, AI artifacts, and extended reading materials
                    that provide deeper context into the modern GeoAI landscape.
                </p>
            </div>

            {resources.length === 0 ? (
                <p className="text-gray-500 italic">No resources available yet.</p>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
                    {resources.map((resource) => (
                        <Link
                            href={`/resources/${resource.slug}`}
                            key={resource.slug}
                            className="block group h-full"
                        >
                            <div className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow p-6 h-full flex flex-col relative overflow-hidden">
                                {/* Status Badge */}
                                <div className="absolute top-4 right-4">
                                    <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border shadow-sm ${getStatusBadgeClasses(resource.status)}`}>
                                        {resource.status}
                                    </span>
                                </div>

                                <h2 className="text-xl font-bold text-blue-700 group-hover:text-blue-500 mb-2 pr-24">
                                    {resource.title}
                                </h2>


                                <div className="mt-auto pt-4 flex flex-col gap-1 text-sm text-gray-500">
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-gray-700">Date:</span>
                                        {resource.date}
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-gray-700">Source:</span>
                                        <span className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded text-xs">{resource.source}</span>
                                    </div>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
