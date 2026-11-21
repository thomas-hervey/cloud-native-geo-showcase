import { redirect } from 'next/navigation';

// /scout has been consolidated into /scout/lab (issue #66)
export default function ScoutRedirect() {
  redirect('/scout/lab');
}
