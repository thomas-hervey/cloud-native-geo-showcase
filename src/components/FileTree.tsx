'use client';

import React from 'react';
import { Folder, FileCode } from 'lucide-react';

interface FileTreeProps {
    content: string;
}

interface TreeNode {
    name: string;
    type: 'file' | 'folder';
    children?: TreeNode[];
    depth: number;
}

const parseTree = (content: string): TreeNode[] => {
    const lines = content.trim().split('\n');
    const root: TreeNode[] = [];
    const stack: { node: TreeNode; indent: number }[] = [];

    lines.forEach((line) => {
        // Basic indentation handling (2 spaces or typical tree characters)
        // We clean up '├──', '└──', '│' characters to just get depth
        const cleanLineCandidate = line.replace(/[│├└─]/g, '').trim();
        if (!cleanLineCandidate) return;

        // Detect indentation level (naive approach: count spaces/tree chars)
        // A better way for simple markdown lists or tree output:
        // We'll trust the user to copy-paste `tree` output or standard indentation
        const indentMatch = line.match(/^[\s│├└─]*/);
        const rawIndent = indentMatch ? indentMatch[0].length : 0;

        // Determine type
        const isFolder = line.endsWith('/');
        const cleanName = cleanLineCandidate.replace(/\/$/, '');

        const newNode: TreeNode = {
            name: cleanName,
            type: isFolder ? 'folder' : 'file',
            children: isFolder ? [] : undefined,
            depth: 0, // Calculated relative to stack
        };

        while (stack.length > 0 && stack[stack.length - 1].indent >= rawIndent) {
            stack.pop();
        }

        if (stack.length === 0) {
            root.push(newNode);
        } else {
            stack[stack.length - 1].node.children?.push(newNode);
        }

        stack.push({ node: newNode, indent: rawIndent });
    });

    return root;
};

// Simplified parser that assumes simple indentation for now
// or standard `tree` command output format handling could be complex.
// Let's stick to a manual parser that expects standard indented text for robustness 
// or just formatting the `tree` output nicely.

// Actually, rendering the `tree` output directly as a pre-formatted block 
// with some syntax highlighting might be safer than trying to parse ASCII art perfectly.
// BUT, the user wants a "visual structure".

const SimpleFileNode = ({ name, type, indent }: { name: string, type: 'file' | 'folder', indent: number }) => (
    <div className="flex items-center py-1" style={{ paddingLeft: `${indent * 20}px` }}>
        {type === 'folder' ? (
            <Folder className="w-4 h-4 mr-2 text-blue-500" />
        ) : (
            <FileCode className="w-4 h-4 mr-2 text-gray-400" />
        )}
        <span className={`text-sm ${type === 'folder' ? 'font-semibold text-gray-700' : 'text-gray-600'}`}>
            {name}
        </span>
    </div>
);

const FileTree: React.FC<FileTreeProps> = ({ content }) => {
    const nodes = parseTree(content);

    const renderNodes = (nodes: TreeNode[], depth = 0) => {
        return nodes.map((node, idx) => (
            <React.Fragment key={`${depth}-${idx}`}>
                <SimpleFileNode name={node.name} type={node.type} indent={depth} />
                {node.children && renderNodes(node.children, depth + 1)}
            </React.Fragment>
        ));
    };

    return (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 my-6 font-mono overflow-auto shadow-sm">
            <div className="text-xs text-gray-400 mb-4 uppercase tracking-widest font-bold flex items-center">
                <Folder className="w-3 h-3 mr-2" />
                Exercise Structure
            </div>
            <div className="space-y-0.5">
                {renderNodes(nodes)}
            </div>
        </div>
    );
};

export default FileTree;
