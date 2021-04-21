import {createBar, failing, getFoo, nextDay, onlyInjectEndpoint} from '../generated/api';

const tests = [
  ['send param, receive payload', async () => {
    const foo = await getFoo('world');
    return foo.oneField === 'hello world';
  }],
  ['send payload, receive nothing', async () => {
    const foo = await onlyInjectEndpoint({oneField: 'inject'});
    return foo === undefined;
  }],
  ['send and receive payload', async () => {
    const foo = await createBar({subField: {oneField: 'post'}, otherField: 'other'});
    return foo.oneField === 'post';
  }],
  ['failing request fails', async () => {
    try {
      await failing();
    } catch (e) {
      return e.response.status === 400;
    }
    return false;
  }],
  ['send and receive datetime', async () => {
    const dateObj = {dt: new Date("2020-02-01T03:02:01Z")};
    const ret = await nextDay(dateObj);
    return ret.getTime() === new Date("2020-02-02T03:02:01Z").getTime();
  }]
]

export default tests;