export function formatDate(dateString: string) {
  const date = new Date(dateString)
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

export function getInitials(email: string) {
  const name = email.split("@")[0]
  return name.slice(0, 2).toUpperCase()
}
