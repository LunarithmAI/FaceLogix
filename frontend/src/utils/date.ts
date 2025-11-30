import { format, formatDistanceToNow, parseISO, isToday, isYesterday } from 'date-fns';

/**
 * Format a date string to a readable format
 * @param dateString - ISO date string
 * @param formatStr - date-fns format string
 * @returns Formatted date string
 */
export function formatDate(dateString: string, formatStr: string = 'PPP'): string {
  try {
    const date = parseISO(dateString);
    return format(date, formatStr);
  } catch {
    return dateString;
  }
}

/**
 * Format a date to time only (e.g., "9:30 AM")
 */
export function formatTime(dateString: string): string {
  return formatDate(dateString, 'p');
}

/**
 * Format a date to date and time (e.g., "Jan 5, 2024, 9:30 AM")
 */
export function formatDateTime(dateString: string): string {
  return formatDate(dateString, 'PPp');
}

/**
 * Format a date to short date (e.g., "Jan 5, 2024")
 */
export function formatShortDate(dateString: string): string {
  return formatDate(dateString, 'PP');
}

/**
 * Format a date to relative time (e.g., "5 minutes ago")
 */
export function formatRelative(dateString: string): string {
  try {
    const date = parseISO(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch {
    return dateString;
  }
}

/**
 * Format a date with smart relative display
 * - Today: "Today at 9:30 AM"
 * - Yesterday: "Yesterday at 9:30 AM"
 * - This week: "Monday at 9:30 AM"
 * - Older: "Jan 5, 2024"
 */
export function formatSmartDate(dateString: string): string {
  try {
    const date = parseISO(dateString);
    
    if (isToday(date)) {
      return `Today at ${format(date, 'p')}`;
    }
    
    if (isYesterday(date)) {
      return `Yesterday at ${format(date, 'p')}`;
    }
    
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
    
    if (diffDays < 7) {
      return format(date, "EEEE 'at' p");
    }
    
    return format(date, 'PP');
  } catch {
    return dateString;
  }
}

/**
 * Format duration in hours and minutes
 * @param minutes - Duration in minutes
 * @returns Formatted duration string (e.g., "8h 30m")
 */
export function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${minutes}m`;
  }
  
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  
  if (mins === 0) {
    return `${hours}h`;
  }
  
  return `${hours}h ${mins}m`;
}

/**
 * Calculate duration between two dates in minutes
 */
export function calculateDuration(startDate: string, endDate: string): number {
  try {
    const start = parseISO(startDate);
    const end = parseISO(endDate);
    return Math.round((end.getTime() - start.getTime()) / (1000 * 60));
  } catch {
    return 0;
  }
}

/**
 * Get start of day as ISO string
 */
export function getStartOfDay(date: Date = new Date()): string {
  const start = new Date(date);
  start.setHours(0, 0, 0, 0);
  return start.toISOString();
}

/**
 * Get end of day as ISO string
 */
export function getEndOfDay(date: Date = new Date()): string {
  const end = new Date(date);
  end.setHours(23, 59, 59, 999);
  return end.toISOString();
}

/**
 * Format a date for API queries (YYYY-MM-DD)
 */
export function formatApiDate(date: Date = new Date()): string {
  return format(date, 'yyyy-MM-dd');
}

/**
 * Format a date string for display (e.g., "Jan 5, 2024")
 * Accepts both ISO date strings and YYYY-MM-DD format
 */
export function formatDisplayDate(dateString: string): string {
  try {
    // Handle YYYY-MM-DD format by parsing as local date
    if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
      const [year, month, day] = dateString.split('-').map(Number);
      const date = new Date(year, month - 1, day);
      return format(date, 'PP');
    }
    // Handle ISO date strings
    const date = parseISO(dateString);
    return format(date, 'PP');
  } catch {
    return dateString;
  }
}
