interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = 'h-4 w-full' }: SkeletonProps) {
  return <div aria-hidden="true" className={`animate-pulse rounded-md bg-navy-700/60 ${className}`} />
}
