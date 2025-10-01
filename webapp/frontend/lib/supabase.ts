import { createClient } from '@supabase/supabase-js'
import { createClientComponentClient, createServerComponentClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables')
}

// For client-side operations
export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// For client components that need auth
export const createClientSupabase = () => createClientComponentClient()

// For server components that need auth
export const createServerSupabase = () => createServerComponentClient({ cookies })

// Database types (to be generated with Supabase CLI)
export type Database = {
  public: {
    Tables: {
      user_profiles: {
        Row: {
          id: string
          email: string | null
          full_name: string | null
          avatar_url: string | null
          role: 'admin' | 'analyst' | 'viewer'
          organization: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id: string
          email?: string | null
          full_name?: string | null
          avatar_url?: string | null
          role?: 'admin' | 'analyst' | 'viewer'
          organization?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          email?: string | null
          full_name?: string | null
          avatar_url?: string | null
          role?: 'admin' | 'analyst' | 'viewer'
          organization?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      properties: {
        Row: {
          id: string
          name: string | null
          address_line1: string | null
          address_line2: string | null
          city: string | null
          province: string | null
          postal_code: string | null
          country: string
          address_canonical: string | null
          address_hash: string | null
          latitude: number | null
          longitude: number | null
          created_at: string
          updated_at: string
        }
      }
      transactions: {
        Row: {
          id: string
          source: string | null
          property_id: string | null
          transaction_date: string | null
          transaction_type: string | null
          price: number | null
          created_at: string
          updated_at: string
        }
      }
      notes: {
        Row: {
          id: string
          entity_type: string
          entity_id: string
          author: string | null
          body: string
          created_at: string
        }
      }
    }
  }
}