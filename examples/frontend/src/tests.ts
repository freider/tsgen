import {createBar, dictTransform, failing, getFoo, nextDay, onlyInjectEndpoint, reverse} from '../generated/api';

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
    return JSON.stringify(ret) == JSON.stringify([13, 37])
  }],
  ['send and receive homogenous dict', async () => {
    const ret = await dictTransform({foo: 5, bar: 17});
    const sameKeys = JSON.stringify(Object.keys(ret).sort()) == JSON.stringify(["foo_trans", "bar_trans"].sort())
    const sameValues = ret["foo_trans"].oneField == "_form5" && ret["bar_trans"].oneField == "_form17";
    return sameKeys && sameValues;
  }],
]

export default tests;