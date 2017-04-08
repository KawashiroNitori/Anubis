/**
 * Created by Nitori on 2017/3/26.
 */
import React from 'react';
import { connect } from 'react-redux';
import i18n from '../../utils/i18n';

import * as util from '../../misc/Util';


const mapStateToProps = (state, ownProps) => ({
    ...ownProps,
    isLoading: state.isPosting || state.isLoading,
});

const mapDispatchToProps = dispatch => ({
    postSend(item) {
        const req = util.post('', {
            operation: 'send',
            tid: item.tid,
            uid: item.uid,
            pid: item.pid,
        });
        dispatch({
            type: 'BALLOON_POST_SEND',
            payload: req,
        });
    },

    postCancel(item) {
        const req = util.post('', {
            operation: 'cancel',
            tid: item.tid,
            uid: item.uid,
            pid: item.pid,
        });
        dispatch({
            type: 'BALLOON_POST_SEND',
            payload: req,
        });
    },
});

@connect(mapStateToProps, mapDispatchToProps)
export default class BalloonPadListItemContainer extends React.PureComponent {
    render() {
        const item = this.props.item;
        return (
            <tr>
                <td className="col--uname">{item.uname}</td>
                <td className="col--nickname">{item.nickname}</td>
                <td className="col--letter">{item.letter}</td>
                <td className="col--balloon">
                    <button
                        disabled={this.props.isLoading}
                        className="link text-maroon lighter"
                        onClick={() => (item.balloon ? this.props.postCancel(item) : this.props.postSend(item))}
                    >
                        {
                            item.balloon
                                ? (<span><span className="icon icon-delete" /> {i18n('Cancel')}</span>)
                                : (<span><span className="icon icon-send" /> {i18n('Send')}</span>)
                        }
                    </button>
                </td>
            </tr>
        );
    }
}
