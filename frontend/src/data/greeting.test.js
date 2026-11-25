import test from 'node:test'
import assert from 'node:assert/strict'
import { displayNameFromUsername, greetingForHour } from './greeting.js'

test('greets people based on local time of day', () => {
  assert.equal(greetingForHour(9), 'Good morning')
  assert.equal(greetingForHour(14), 'Good afternoon')
  assert.equal(greetingForHour(20), 'Good evening')
})

test('formats account usernames as display names', () => {
  assert.equal(displayNameFromUsername('nikhita_'), 'Nikhita')
  assert.equal(displayNameFromUsername('alex.morgan'), 'Alex Morgan')
  assert.equal(displayNameFromUsername(''), 'there')
})
