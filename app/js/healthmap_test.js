
function testZfill() {
  assertEquals('001', zfill(1, 3), 'Should z-fill properly');
  assertEquals('2', zfill(2, 1), 'Should z-fill properly');
}
