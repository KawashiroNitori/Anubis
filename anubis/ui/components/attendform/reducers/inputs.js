/**
 * Created by Nitori on 2017/4/4.
 */

const initialSubState = {
    value: '',
    isCorrect: false,
    isBlur: false,
    errInfo: '',
};

export default function reducer(state = {}, action) {
    if (!action.payload) {
        return state;
    }
    const name = action.payload.name;
    let result = state[name] ? { ...state[name] } : initialSubState;
    switch (action.type) {
        case 'INPUT_INIT': {
            result = {
                ...result,
                ...action.payload,
            };
            break;
        }
        case 'INPUT_CHANGED': {
            result = {
                ...result,
                value: action.payload.value,
            };
            break;
        }
        case 'INPUT_CHANGE_TO_CORRECT': {
            result = {
                ...result,
                isCorrect: true,
                errInfo: '',
            };
            break;
        }
        case 'INPUT_CHANGE_TO_INCORRECT': {
            result = {
                ...result,
                isCorrect: false,
                errInfo: action.payload.errInfo,
            };
            break;
        }
        case 'INPUT_BLURRED': {
            result = {
                ...result,
                isBlur: true,
            };
            break;
        }
        case 'INPUT_FOCUSED': {
            result = {
                ...result,
                isBlur: false,
            };
            break;
        }
        default:
            return state;
    }
    return {
        ...state,
        [name]: result,
    };
}
