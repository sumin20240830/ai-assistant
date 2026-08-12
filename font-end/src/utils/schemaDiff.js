function isEqual(before, after) {
  return JSON.stringify(before) === JSON.stringify(after)
}

function compareProperties(before, after, ignoredKeys = []) {
  const ignored = new Set(ignoredKeys)
  const propertyNames = new Set([
    ...Object.keys(before ?? {}),
    ...Object.keys(after ?? {}),
  ])

  return [...propertyNames]
    .filter((property) => !ignored.has(property))
    .filter((property) => !isEqual(before?.[property], after?.[property]))
    .map((property) => ({
      property,
      before: before?.[property],
      after: after?.[property],
    }))
}

export function diffSchemas(beforeSchema, afterSchema) {
  const beforeFields = Array.isArray(beforeSchema?.fields)
    ? beforeSchema.fields
    : []
  const afterFields = Array.isArray(afterSchema?.fields)
    ? afterSchema.fields
    : []

  const beforeMap = new Map(
    beforeFields.map((field) => [field.fieldCode, field]),
  )
  const afterMap = new Map(
    afterFields.map((field) => [field.fieldCode, field]),
  )

  const added = []
  const removed = []
  const modified = []

  for (const [fieldCode, afterField] of afterMap) {
    const beforeField = beforeMap.get(fieldCode)

    if (!beforeField) {
      added.push(afterField)
      continue
    }

    const changes = compareProperties(beforeField, afterField)

    if (changes.length > 0) {
      modified.push({
        fieldCode,
        fieldName: afterField.fieldName,
        changes,
      })
    }
  }

  for (const [fieldCode, beforeField] of beforeMap) {
    if (!afterMap.has(fieldCode)) {
      removed.push(beforeField)
    }
  }

  const entityChanges = compareProperties(
    beforeSchema,
    afterSchema,
    ['fields'],
  )

  return {
    entityChanges,
    added,
    removed,
    modified,
    total:
      entityChanges.length +
      added.length +
      removed.length +
      modified.length,
  }
}
