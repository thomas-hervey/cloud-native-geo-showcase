import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const mod = searchParams.get('module');
  
  if (!mod) {
    return NextResponse.json(
      { error: 'Module parameter is required' },
      { status: 400 }
    );
  }
  
  // Sanitize module name to prevent directory traversal
  const sanitizedModule = mod.replace(/[^a-zA-Z0-9-]/g, '');
  
  // Construct the path to the README file
  const readmePath = path.join(process.cwd(), 'src', 'exercises', sanitizedModule, 'README.md');
  
  try {
    // Check if the file exists
    if (!fs.existsSync(readmePath)) {
      return NextResponse.json(
        { error: `README for module ${sanitizedModule} not found` },
        { status: 404 }
      );
    }
    
    // Read the file content
    const content = fs.readFileSync(readmePath, 'utf-8');
    
    // Return the content as plain text
    return new NextResponse(content, {
      headers: {
        'Content-Type': 'text/plain',
      },
    });
  } catch (error) {
    console.error(`Error reading README for module ${sanitizedModule}:`, error);
    return NextResponse.json(
      { error: 'Failed to read README file' },
      { status: 500 }
    );
  }
}
