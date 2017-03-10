/**
 * Created by Nitori on 2016/12/30.
 */
import attachObjectMeta from './util/objectMeta';

// Please note that accepted < others.
export const STATUS_WAITING = 0;
export const STATUS_ACCEPTED = 1;
export const STATUS_WRONG_ANSWER = 2;
export const STATUS_TIME_LIMIT_EXCEEDED = 3;
export const STATUS_MEMORY_LIMIT_EXCEEDED = 4;
export const STATUS_OUTPUT_LIMIT_EXCEEDED = 5;
export const STATUS_RUNTIME_ERROR = 6;
export const STATUS_COMPILE_ERROR = 7;
export const STATUS_SYSTEM_ERROR = 8;
export const STATUS_CANCELLED = 9;
export const STATUS_ETC = 10;
export const STATUS_JUDGING = 20;
export const STATUS_COMPILING = 21;
export const STATUS_FETCHED = 22;
export const STATUS_IGNORED = 30;

export const TYPE_SUBMISSION = 0;
export const TYPE_PRETEST = 1;

export const MODE_COMPARE_IGNORE_BLANK = 0;
export const MODE_COMPARE = 1;
export const MODE_SPECIAL_JUDGE = 2;

export const STATUS_TEXTS = {
    [STATUS_WAITING]: 'Waiting',
    [STATUS_ACCEPTED]: 'Accepted',
    [STATUS_WRONG_ANSWER]: 'Wrong Answer',
    [STATUS_TIME_LIMIT_EXCEEDED]: 'Time Exceeded',
    [STATUS_MEMORY_LIMIT_EXCEEDED]: 'Memory Exceeded',
    [STATUS_OUTPUT_LIMIT_EXCEEDED]: 'Output Exceeded',
    [STATUS_RUNTIME_ERROR]: 'Runtime Error',
    [STATUS_COMPILE_ERROR]: 'Compile Error',
    [STATUS_SYSTEM_ERROR]: 'System Error',
    [STATUS_CANCELLED]: 'Cancelled',
    [STATUS_ETC]: 'Unknown Error',
    [STATUS_JUDGING]: 'Running',
    [STATUS_COMPILING]: 'Compiling',
    [STATUS_FETCHED]: 'Fetched',
    [STATUS_IGNORED]: 'Ignored',
};
attachObjectMeta(STATUS_TEXTS, 'intKey', true);

export const STATUS_CODES = {
    [STATUS_WAITING]: 'pending',
    [STATUS_ACCEPTED]: 'pass',
    [STATUS_WRONG_ANSWER]: 'fail',
    [STATUS_TIME_LIMIT_EXCEEDED]: 'fail',
    [STATUS_MEMORY_LIMIT_EXCEEDED]: 'fail',
    [STATUS_OUTPUT_LIMIT_EXCEEDED]: 'fail',
    [STATUS_RUNTIME_ERROR]: 'fail',
    [STATUS_COMPILE_ERROR]: 'fail',
    [STATUS_SYSTEM_ERROR]: 'ignored',
    [STATUS_CANCELLED]: 'ignored',
    [STATUS_ETC]: 'ignored',
    [STATUS_JUDGING]: 'progress',
    [STATUS_COMPILING]: 'progress',
    [STATUS_FETCHED]: 'progress',
    [STATUS_IGNORED]: 'ignored',
};

attachObjectMeta(STATUS_CODES, 'intKey', true);

// Whether to show detail about each test case for a submission status

export const STATUS_SCRATCHPAD_SHOW_DETAIL_FLAGS = {
    [STATUS_WAITING]: false,
    [STATUS_ACCEPTED]: true,
    [STATUS_WRONG_ANSWER]: true,
    [STATUS_TIME_LIMIT_EXCEEDED]: true,
    [STATUS_MEMORY_LIMIT_EXCEEDED]: true,
    [STATUS_RUNTIME_ERROR]: true,
    [STATUS_COMPILE_ERROR]: false,
    [STATUS_SYSTEM_ERROR]: false,
    [STATUS_CANCELLED]: false,
    [STATUS_ETC]: false,
    [STATUS_JUDGING]: false,
    [STATUS_COMPILING]: false,
    [STATUS_FETCHED]: false,
    [STATUS_IGNORED]: false,
};
attachObjectMeta(STATUS_SCRATCHPAD_SHOW_DETAIL_FLAGS, 'exportToPython', false);

// Short to show in Scratchpad mode

export const STATUS_SCRATCHPAD_SHORT_TEXTS = {
    [STATUS_ACCEPTED]: 'AC',
    [STATUS_WRONG_ANSWER]: 'WA',
    [STATUS_TIME_LIMIT_EXCEEDED]: 'TLE',
    [STATUS_MEMORY_LIMIT_EXCEEDED]: 'MLE',
    [STATUS_RUNTIME_ERROR]: 'RTE',
};
attachObjectMeta(STATUS_SCRATCHPAD_SHORT_TEXTS, 'exportToPython', false);

export const TYPE_TEXTS = {
    [TYPE_SUBMISSION]: 'Submission',
    [TYPE_PRETEST]: 'Pretest',
};
attachObjectMeta(TYPE_TEXTS, 'intKey', true);

export const MODE_TEXTS = {
    [MODE_COMPARE_IGNORE_BLANK]: 'Compare (Ignore Ending Blank)',
    [MODE_COMPARE]: 'Compare',
    [MODE_SPECIAL_JUDGE]: 'Special Judge',
};
attachObjectMeta(MODE_TEXTS, 'intKey', true);
