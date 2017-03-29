/**
 * Created by Nitori on 2017/3/26.
 */
import _ from 'lodash';
import Notification from '../notification';
import i18n from '../../utils/i18n';


export default function reducer(state = {
    pending: [],
    sent: [],
    isLoading: false,
    isPosting: false,
}, action) {
    switch (action.type) {
        case 'BALLOON_MESSAGE_PUSH': {
            let pending = state.pending;
            let sent = state.sent;
            const msg = action.payload;
            const isEqual = item => (
                !(item.uid === msg.uid
                && item.pid === msg.pid
                && item.tid === msg.tid)
            );
            if (msg.balloon) {
                pending = pending.filter(isEqual);
                sent.push(msg);
                sent = _.uniq(sent);
            } else {
                pending.push(msg);
                pending = _.uniq(pending);
                sent = sent.filter(isEqual);
            }
            Notification.info(i18n('Balloon information changed.'));
            return {
                ...state,
                pending,
                sent,
            };
        }
        case 'BALLOON_POST_SEND_PENDING': {
            return {
                ...state,
                isPosting: true,
            };
        }
        case 'BALLOON_POST_SEND_FULFILLED': {
            return {
                ...state,
                isPosting: false,
            };
        }
        case 'BALLOON_POST_SEND_REJECTED': {
            Notification.error(i18n(action.payload.message));
            return {
                ...state,
                isPosting: false,
            };
        }
        case 'BALLOON_LOAD_PENDING': {
            return {
                ...state,
                isLoading: true,
            };
        }
        case 'BALLOON_LOAD_FULFILLED': {
            const pending = action.payload.balloons;
            return {
                ...state,
                pending,
                sent: [],
                isLoading: false,
            };
        }
        case 'BALLOON_LOAD_REJECTED': {
            Notification.error(i18n(action.payload.message));
            return {
                ...state,
                isLoading: false,
            };
        }

        default:
            return state;
    }
}
