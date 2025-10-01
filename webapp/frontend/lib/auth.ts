import { User } from '@supabase/supabase-js'
import { Database } from './supabase'

export type UserProfile = Database['public']['Tables']['user_profiles']['Row']
export type UserRole = 'admin' | 'analyst' | 'viewer'

export interface AuthUser extends User {
  profile?: UserProfile
}

export const roleHierarchy: Record<UserRole, number> = {
  admin: 3,
  analyst: 2,
  viewer: 1
}

export function hasPermission(userRole: UserRole, requiredRole: UserRole): boolean {
  return roleHierarchy[userRole] >= roleHierarchy[requiredRole]
}

export function canManageUsers(userRole: UserRole): boolean {
  return userRole === 'admin'
}

export function canEditData(userRole: UserRole): boolean {
  return hasPermission(userRole, 'analyst')
}

export function canViewData(userRole: UserRole): boolean {
  return hasPermission(userRole, 'viewer')
}

export const roleLabels: Record<UserRole, string> = {
  admin: 'Administrator',
  analyst: 'Data Analyst',
  viewer: 'Viewer'
}

export const roleDescriptions: Record<UserRole, string> = {
  admin: 'Full access to all data and user management',
  analyst: 'Can view and edit properties, transactions, and notes',
  viewer: 'Can view data but cannot make changes'
}