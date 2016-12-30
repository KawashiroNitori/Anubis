/**
 * Created by Nitori on 2016/12/30.
 */
import attachObjectMeta from './util/objectMeta';

export const LANG_TEXTS = {
    c: 'C',
    cc: 'C++',
    java: 'Java',
};
export const LANG_CODEMIRROR_MODES = {
    c: 'text/x-csrc',
    cc: 'text/x-c++src',
    java: 'text/x-java',
};
attachObjectMeta(LANG_CODEMIRROR_MODES, 'exportToPython', false);
