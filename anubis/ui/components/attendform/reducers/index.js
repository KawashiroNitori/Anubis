/**
 * Created by Nitori on 2017/4/4.
 */
import { combineReducers } from 'redux';

import members from './members';
import inputs from './inputs';

const reducer = combineReducers({
    members,
    inputs,
});

export default reducer;
