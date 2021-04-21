import {createBar, failing, getFoo, nextDay, onlyInjectEndpoint, reverse} from '../generated/api';

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
    const ret = await nextDay(new Date("2020-02-01T03:02:01Z"));
    return ret.getTime() === new Date("2020-02-02T03:02:01Z").getTime();
  }],
  ['send and receive list', async () => {
    const ret = await reverse([37, 13]);
    return ret.length == 2 && ret[0] == 13 && ret[1] == 37
  }],
]

export default tests;