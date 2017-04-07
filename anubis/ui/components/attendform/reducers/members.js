/**
 * Created by Nitori on 2017/4/4.
 */
import _ from 'lodash';

import i18n from '../../../utils/i18n';
import Notification from '../../notification';

const initialState = {
    members: [],
    studentId: '',
    citizenId: '',
    isPosting: false,
};

export default function reducer(state = initialState, action) {
    switch (action.type) {
        case 'STUDENT_INIT': {
            return {
                ...state,
                members: [...action.payload],
            };
        }
        case 'STUDENT_INPUT_CHANGED': {
            return {
                ...state,
                [action.payload.name]: action.payload.value,
            };
        }
        case 'STUDENT_ADD_PENDING': {
            return {
                ...state,
                isPosting: true,
            };
        }
        case 'STUDENT_ADD_REJECTED': {
            Notification.error(i18n('Student Verify Failed.'));
            return {
                ...state,
                isPosting: false,
            };
        }
        case 'STUDENT_ADD_FULFILLED': {
            let members = state.members;
            members.push(action.payload);
            members = _.uniqBy(members, '_id');
            return {
                ...state,
                members,
                isPosting: false,
                studentId: '',
                citizenId: '',
            };
        }
        case 'STUDENT_REMOVE': {
            let members = [...state.members];
            members = members.filter(item => (item._id !== action.payload));
            return {
                ...state,
                members,
            };
        }
        default:
            return state;
    }
}
