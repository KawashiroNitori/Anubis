/**
 * Created by Nitori on 2017/4/4.
 */
import { combineReducers } from 'redux';

import members from './members';
import inputs from './inputs';
import newbie from './newbie';

const reducer = combineReducers({
    members,
    inputs,
    newbie,
});

export default reducer;
