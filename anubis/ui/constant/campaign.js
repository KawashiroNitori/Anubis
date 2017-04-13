/**
 * Created by Nitori on 2017/4/13.
 */
import attachObjectMeta from './util/objectMeta';

export const GRADE_ID = {
    1: 'freshman',
    2: 'sophomore',
    3: 'junior',
    4: 'senior',
};

attachObjectMeta(GRADE_ID, 'intKey', true);

export const GRADE_NAME = {
    1: 'Freshman',
    2: 'Sophomore',
    3: 'Junior',
    4: 'Senior',
};

attachObjectMeta(GRADE_NAME, 'intKey', true);
