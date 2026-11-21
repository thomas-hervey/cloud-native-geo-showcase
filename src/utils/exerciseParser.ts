/**
 * Utility functions to extract exercise data from markdown content
 */

export interface Exercise {
  title: string;
  description: string;
  language: string;
  code: string;
  instructions?: string;
}

/**
 * Extracts exercises from markdown content
 * Looks for sections marked with ## Exercise: [title]
 * and code blocks within those sections
 */
export function extractExercisesFromMarkdown(markdown: string): Exercise[] {
  const exercises: Exercise[] = [];
  
  // Match exercise sections - starts with ## Exercise: and ends before the next heading
  const exerciseRegex = /## Exercise: ([\s\S]*?)(?=\n#|\n$)/g;
  let exerciseMatch;
  
  while ((exerciseMatch = exerciseRegex.exec(markdown)) !== null) {
    const fullExerciseText = exerciseMatch[0];
    const title = exerciseMatch[1].trim();
    
    // Extract description (text before the first code block)
    const descriptionMatch = fullExerciseText.match(/## Exercise: [\s\S]*?\n([\s\S]*?)(?=```)/);
    const description = descriptionMatch ? descriptionMatch[1].trim() : '';
    
    // Extract instructions (text marked with > or blockquote)
    const instructionsMatch = fullExerciseText.match(/>([\s\S]*?)(?=```|\n\n)/);
    const instructions = instructionsMatch ? instructionsMatch[1].trim() : undefined;
    
    // Extract code blocks
    const codeBlockRegex = /```(\w+)\n([\s\S]*?)```/g;
    let codeBlockMatch;
    
    while ((codeBlockMatch = codeBlockRegex.exec(fullExerciseText)) !== null) {
      const language = codeBlockMatch[1];
      const code = codeBlockMatch[2];
      
      exercises.push({
        title,
        description,
        language,
        code,
        instructions
      });
      
      // If we want only the first code block per exercise, uncomment this break
      // break;
    }
  }
  
  return exercises;
}

/**
 * Alternative method to extract exercises from Python files
 * This can be used if exercises are stored in separate Python files
 */
export async function loadExerciseFromFile(filePath: string): Promise<Exercise | null> {
  try {
    const response = await fetch(filePath);
    if (!response.ok) {
      throw new Error(`Failed to load exercise file: ${filePath}`);
    }
    
    const code = await response.text();
    const filename = filePath.split('/').pop() || '';
    
    // Extract title and description from comments at the top of the file
    const titleMatch = code.match(/# Title: (.*)/);
    const descriptionMatch = code.match(/# Description: (.*)/);
    
    return {
      title: titleMatch ? titleMatch[1] : filename,
      description: descriptionMatch ? descriptionMatch[1] : 'No description available',
      language: 'python',
      code
    };
  } catch (error) {
    console.error('Error loading exercise file:', error);
    return null;
  }
}
