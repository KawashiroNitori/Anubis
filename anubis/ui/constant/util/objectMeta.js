/**
 * Created by Nitori on 2016/12/30.
 */
export default function attachObjectMeta(obj, key, value) {
    Object.defineProperty(obj, `__${key}`, {
        value,
        enumerable: false,
        configurable: false,
        writable: false,
    });
}