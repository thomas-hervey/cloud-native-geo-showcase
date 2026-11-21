import Link from 'next/link';
import { FC } from 'react';

interface ModuleCardProps {
  id: string;
  title: string;
  description: string;
  slug: string;
}

const ModuleCard: FC<ModuleCardProps> = ({ id, title, description, slug }) => {
  return (
    <Link
      href={`/cng-modules/${slug}`}
      className="block p-6 bg-white rounded-lg border border-gray-200 shadow-md hover:bg-gray-100 transition-colors"
    >
      <div className="flex items-start">
        <div className="flex-shrink-0 inline-flex items-center justify-center h-10 w-10 rounded-full bg-blue-500 text-white font-semibold mr-4">
          {id}
        </div>
        <div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">{title}</h3>
          <p className="text-gray-700">{description}</p>
        </div>
      </div>
    </Link>
  );
};

export default ModuleCard;
