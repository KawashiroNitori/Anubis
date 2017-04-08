/**
 * Created by Nitori on 2017/4/3.
 */
import React from 'react';
import { connect } from 'react-redux';

import i18n from '../../utils/i18n';
import Notification from '../notification';
import * as utils from '../../misc/Util';
import AttendFormMemberContainer from './AttendFormMemberContainer';
import AttendFormTextboxContainer from './AttendFormTextboxContainer';


const mailValidator = {
    mail: {
        presence: true,
        format: {
            pattern: /\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*/,
            message: '{0} is invalid.',
        },
    },
};

const telValidator = {
    tel: {
        presence: true,
        format: {
            pattern: /^1(3|4|5|7|8)[0-9]\d{8}$/,
            message: '{0} is invalid.',
        },
    },
};

const teamNameValidator = {
    team_name: {
        presence: true,
        format: {
            pattern: /^[a-zA-Z0-9\u4e00-\u9fa5][a-zA-Z0-9 \u4e00-\u9fa5]{1,14}[a-zA-Z0-9\u4e00-\u9fa5]$/,
            message: '{0} is invalid.',
        },
    },
};

const thisYear = new Date().getFullYear();

const mapStateToProps = (state, ownProps) => ({
    ...ownProps,
    ...state,
    allCorrect: (state.inputs.mail ? state.inputs.mail.isCorrect : false)
    && (state.inputs.tel ? state.inputs.tel.isCorrect : false)
    && (state.inputs.team_name ? state.inputs.team_name.isCorrect : false)
    && state.members.members.length > 0,
    isNewbie: state.newbie.isNewbie,
    canNewbie: state.members.members.reduce((acc, val) => acc && val.grade === thisYear, true),
    handleSubmit(e) {
        e.preventDefault();
        const member_id = state.members.members.map(item => item._id);
        const member_id_number = state.members.members.map(item => item.id_number.slice(-6));
        const data = {
            mail: state.inputs.mail.value,
            tel: state.inputs.tel.value,
            team_name: state.inputs.team_name.value,
            is_newbie: Context.enableNewbie && state.newbie.isNewbie ? 'on' : '',
            member_id,
            member_id_number,
        };
        utils
            .post('', data)
            .then((res) => window.location.replace(res.redirect))
            .catch(() => {
                Notification.error('Attend Failed.');
            });
    },
});

const mapDispatchToProps = (dispatch) => ({
    initInput(...name) {
        name.map(item => (dispatch({
            type: 'INPUT_INIT',
            payload: item,
        })));
    },
    initMembers(members) {
        dispatch({
            type: 'STUDENT_INIT',
            payload: members,
        });
    },
    handleNewbieChanged(is_newbie) {
        dispatch({
            type: 'NEWBIE_CHECKBOX_CHANGED',
            payload: is_newbie,
        });
    },

});

@connect(mapStateToProps, mapDispatchToProps)
export default class AttendFormContainer extends React.PureComponent {
    componentWillMount() {
        const teamInfo = Context.teamInfo;
        this.props.initInput({
            name: 'mail',
            value: teamInfo.mail,
        }, {
            name: 'tel',
            value: teamInfo.tel,
        }, {
            name: 'team_name',
            value: teamInfo.team_name,
        });
        this.props.initMembers(teamInfo.members);
        this.props.handleNewbieChanged(teamInfo.is_newbie);
    }

    render() {
        return (
            <div className="attendform">
                <form onSubmit={this.props.handleSubmit}>
                    <div className="row">
                        <AttendFormTextboxContainer
                            columns="6"
                            name="mail"
                            labelName="Email"
                            constraints={mailValidator}
                        />
                        <AttendFormTextboxContainer
                            columns="6"
                            name="tel"
                            labelName="Telephone"
                            constraints={telValidator}
                        />
                    </div>
                    <AttendFormTextboxContainer
                        columns="12"
                        row="true"
                        name="team_name"
                        labelName="Team Name"
                        placeholder="4-16 chinese, english characters, numbers or spaces."
                        constraints={teamNameValidator}
                    />
                    <div className="row">
                        <div className="medium columns">
                            <AttendFormMemberContainer />
                        </div>
                    </div>
                    {Context.enableNewbie &&
                    <div className="row"><div className="medium columns">
                        <label className="checkbox">
                            <input
                                type="checkbox"
                                name="newbie"
                                checked={this.props.isNewbie}
                                onChange={(e) => this.props.handleNewbieChanged(e.target.checked)}
                                disabled={!this.props.canNewbie}
                            />
                            {i18n('Newbie')}{' '}
                            <span
                                className="icon icon-help"
                                data-tooltip={i18n('Only freshmen is allowed.')}
                            />
                        </label>
                    </div></div>
                    }
                    <button
                        className="rounded primary button submit-button"
                        type="submit"
                        onClick={this.handleSubmit}
                        disabled={!this.props.allCorrect}
                    >
                        {i18n('Attend')}
                    </button>
                </form>
            </div>
        );
    }
}
