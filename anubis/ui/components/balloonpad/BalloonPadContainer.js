/**
 * Created by Nitori on 2017/3/26.
 */
import React from 'react';
import { connect } from 'react-redux';

import * as util from '../../misc/Util';
import i18n from '../../utils/i18n';
import BalloonPadListContainer from './BalloonPadListContainer';

const mapStateToProps = (state, ownProps) => ({
    ...ownProps,
    pending: state.pending,
    sent: state.sent,
});

const mapDispatchToProps = dispatch => ({
    loadBalloons() {
        dispatch({
            type: 'BALLOON_LOAD',
            payload: util.get(''),
        });
    },
});

@connect(mapStateToProps, mapDispatchToProps)
export default class BalloonPadContainer extends React.PureComponent {
    componentDidMount() {
        this.props.loadBalloons();
    }

    render() {
        return (
            <div className="balloonpad clearfix">
                <div className="balloonpad__list float-left">
                    <div className="section__header">
                        <h1 className="section__title">{i18n('Pending Balloon')}</h1>
                    </div>
                    <BalloonPadListContainer list={this.props.pending} />
                </div>
                <div className="balloonpad__list float-right">
                    <div className="section__header">
                        <h1 className="section__title">{i18n('Sent Balloon')}</h1>
                    </div>
                    <BalloonPadListContainer list={this.props.sent} />
                </div>
            </div>
        );
    }
}
