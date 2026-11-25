export function greetingForHour(hour = new Date().getHours()) {
  if (hour >= 5 && hour < 12) return 'Good morning'
  if (hour >= 12 && hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export function displayNameFromUsername(username) {
  const parts = username?.split(/[._-]+/).filter(Boolean) || []
  return parts.length
    ? parts.map((part) => part[0].toUpperCase() + part.slice(1)).join(' ')
    : 'there'
}
