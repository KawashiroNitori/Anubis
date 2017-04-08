/**
 * Created by Nitori on 2017/4/7.
 */
export default function reducer(state = { isNewbie: false }, action) {
    const thisYear = new Date().getFullYear();
    switch (action.type) {
        case 'NEWBIE_INIT': {
            return {
                ...state,
                ...action.payload,
            };
        }
        case 'NEWBIE_CHECKBOX_CHANGED': {
            return {
                ...state,
                isNewbie: action.payload,
            };
        }
        case 'STUDENT_ADD_FULFILLED': {
            const newbie = action.payload.grade === thisYear;
            return {
                ...state,
                isNewbie: state.isNewbie && newbie,
            };
        }
        default:
            return state;
    }
}
