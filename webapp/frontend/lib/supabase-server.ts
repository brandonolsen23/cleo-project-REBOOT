import { createServerComponentClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'

// For server components that need auth
export const createServerSupabase = () => createServerComponentClient({ cookies })
